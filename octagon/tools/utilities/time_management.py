import json
import os.path
import time


def wait(seconds: int):
    """
    Function simply waits a number of seconds to accompany market movements later
    :param seconds: time to wait in seconds
    :return:
    """
    time.sleep(seconds)

    return f"Waited {seconds}"


def write_memory(content: str):
    """
    Write to memory so that agent can remember what it did the last time.
    Memory is restricted to seven entries.
    """
    raw_memory = read_memory_raw()

    while len(raw_memory) >= 7:
        raw_memory.pop(0)

    raw_memory.append(
        {
            "datetime": int(time.time()),
            "entry": content,
        }
    )

    with open("memory.json", "w") as f:
        json.dump(raw_memory, f)

    return "Wrote successfully to memory."


def stop(memory: str):
    """
    Stop running the agent at the end of trading day
    """
    if memory is not None and len(memory) > 0:
        write_memory(memory)

    return "Stopped!"


def read_memory() -> str:
    """
    Read and format the memory for the agent
    :return: Formatted memory for the agent
    """
    raw_memory = read_memory_raw()
    return format_memory(raw_memory)


def format_memory(raw_memory: list) -> str:
    """
    Format the memory for the agent
    :return: Formatted memory for the agent
    """
    if len(raw_memory) == 0:
        return "No previous memory."

    formatted_memory = ""
    for num, item in enumerate(raw_memory):
        formatted_memory += f"===== Entry {num + 1} =====\n\n{item['entry']}\n\n"

    return formatted_memory


def read_memory_raw() -> list:
    """
    Read memory from the JSON file and return it as a raw list unsuitable for a string output.
    """
    if not os.path.exists("memory.json"):
        return []

    with open("memory.json", "r") as f:
        memory = json.load(f)
        sorted(memory, key=lambda x: x["datetime"])

        return memory
