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
    Write to memory so that agent can remember what it did the last time
    """
    with open("memory.txt", "w") as f:
        f.write(content)
    return "Wrote successfully to memory."


def stop(memory: str | None = None):
    """
    Stop running the agent at the end of trading day
    """
    if memory is not None and len(memory) > 0:
        write_memory(memory)

    return "Stopped!"
