"""
Command registry for STS AI Lab.

Maps command names to handler functions.
"""

from app.command_handlers import tools_handler, tree_handler, read_handler


COMMANDS = {}


def register(command: str, handler):
    """
    Register a command handler.
    """
    COMMANDS[command] = handler


def get_handler(command: str):
    """
    Return the registered handler, or None.
    """
    return COMMANDS.get(command)


def list_registered_commands():
    """
    Return registered command names.
    """
    return sorted(COMMANDS.keys())


register("/tools", tools_handler)

register("/tree", tree_handler)

register("/read", read_handler)
