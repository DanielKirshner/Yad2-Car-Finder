import importlib


def test_bot_imports_on_this_python_version():
    """Importing main pulls in every module and dependency the bot needs to start."""
    importlib.import_module("main")
