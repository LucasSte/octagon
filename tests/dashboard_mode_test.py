import os
import unittest
from datetime import date
from unittest.mock import patch

from textual.widgets import Input, RichLog, Select, Static

from octagon.agent.trader_agent import TraderAgent
from octagon.dashboard.dashboard import LIVE_MODE, SIMULATION_MODE, Dashboard
from octagon.simulation.clock import RealClock, get_clock
from octagon.simulation.replay import disable_replay
from octagon.tools.utilities import time_management


def log_text(app) -> str:
    return "\n".join(line.text for line in app.query_one("#bottom_left", RichLog).lines)


@patch("octagon.dashboard.dashboard.check_replay_day", return_value=(None, None))
class DashboardModeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.agent = TraderAgent(1, "prompt", "http://localhost:1", "model", True)

    def tearDown(self):
        disable_replay()
        if os.path.exists("memory_replay.json"):
            os.remove("memory_replay.json")

    async def submit_day(self, app, pilot, text):
        box = app.query_one("#sim_date", Input)
        box.value = text
        box.focus()
        await pilot.press("enter")
        await pilot.pause()

    async def test_select_simulation_day_then_back_to_live(self, _check):
        app = Dashboard(self.agent)
        async with app.run_test(size=(160, 50)) as pilot:
            self.assertEqual(app.query_one("#mode_select", Select).value, LIVE_MODE)

            await self.submit_day(app, pilot, "2026-11-20 10:15")
            self.assertEqual(self.agent.replay.day, date(2026, 11, 20))
            self.assertEqual(f"{get_clock().now():%Y-%m-%d %H:%M}", "2026-11-20 10:15")
            self.assertEqual(time_management.MEMORY_FILE, "memory_replay.json")
            self.assertEqual(
                app.query_one("#mode_select", Select).value, SIMULATION_MODE
            )
            panel = app.query_one("#top_row_right", Static).content
            self.assertIn("2026-11-20 10:15", str(panel.renderable))

            app.query_one("#mode_select", Select).value = LIVE_MODE
            await pilot.pause()
            self.assertIsNone(self.agent.replay)
            self.assertIsInstance(get_clock(), RealClock)

    async def test_selecting_simulation_without_day_asks_for_one(self, _check):
        app = Dashboard(self.agent)
        async with app.run_test(size=(160, 50)) as pilot:
            app.query_one("#mode_select", Select).value = SIMULATION_MODE
            await pilot.pause()
            self.assertIsNone(self.agent.replay)
            self.assertIn("Type the day to simulate", log_text(app))

    async def test_invalid_day_is_rejected(self, _check):
        app = Dashboard(self.agent)
        async with app.run_test(size=(160, 50)) as pilot:
            await self.submit_day(app, pilot, "20/11/2026")
            self.assertIsNone(self.agent.replay)
            self.assertIn("Invalid day to simulate", log_text(app))

    async def test_mode_cannot_change_while_agent_runs(self, _check):
        app = Dashboard(self.agent)
        async with app.run_test(size=(160, 50)) as pilot:
            app.active_worker = object()
            await self.submit_day(app, pilot, "2026-11-20")
            self.assertIsNone(self.agent.replay)
            self.assertIn("Stop the agent", log_text(app))
            app.active_worker = None


if __name__ == "__main__":
    unittest.main()
