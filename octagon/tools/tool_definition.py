from collections.abc import Callable


class ToolDefinition:
    def description(self) -> list[dict]:
        """
        Return a description of the available functions for this tool
        according to the standardized format.
        :return:
        """

    def dispatch_dictionary(self) -> dict[str, Callable]:
        """
        Return a dictionary matching the function name and its callable pointer.
        :return:
        """
