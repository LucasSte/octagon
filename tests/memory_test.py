import os
import unittest

from octagon.tools.utilities.time_management import (
    read_memory,
    read_memory_raw,
    write_memory,
)


class TestMemory(unittest.TestCase):
    @classmethod
    def tearDown(cls):
        os.remove("memory.json")

    def test_read_and_write(self):
        write_memory("first entry")
        write_memory("second entry")

        raw_memory = read_memory_raw()
        self.assertEqual(raw_memory[0]["entry"], "first entry")
        self.assertEqual(raw_memory[1]["entry"], "second entry")

    def test_seven_entries_limit(self):
        for i in range(10):
            write_memory(f"entry no: {i}")

        raw_memory = read_memory_raw()
        self.assertEqual(len(raw_memory), 7)
        for num, item in enumerate(raw_memory):
            self.assertEqual(item["entry"], f"entry no: {num + 3}")

    def test_formatting(self):
        write_memory("first item")
        write_memory("second item")

        print(read_memory())
