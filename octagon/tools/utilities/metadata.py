"""
Dictionary containing descriptions of functions for use by language models.
These functions are designed to be used as tools by agents to provide financial analysis.
"""

from octagon.tools.utilities.time_management import stop, wait, write_memory

DESCRIPTION_LIST = [
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait a number of second to monitor the market later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "The number of seconds to wait.",
                    }
                },
                "required": ["seconds"],
            },
            "returns": {
                "type": "string",
                "description": "A message confirming the waited time.",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_memory",
            "description": "Write something to permanent memory so that your future self remember "
            "what you did in the previous run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Summary of what you did in this run.",
                    }
                },
                "required": ["content"],
            },
            "returns": {
                "type": "string",
                "description": "A message confirming the action.",
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop",
            "description": "Stop current trading session and only continue tomorrow",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "An optional summary of what you did in this run.",
                    }
                },
                "required": [],
            },
            "returns": {
                "type": "string",
                "description": "A message confirming the stop.",
            },
        },
    },
]

DISPATCH_DICT = {
    "wait": wait,
    "write_memory": write_memory,
    "stop": stop,
}
