"""A versatile integration testing framework for django apps."""

import logging
from typing import Any

from rich.console import Console

class SceneryLogger:

    style_map = {
        logging.DEBUG: None,
        logging.INFO: "blue",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
    }

    def __init__(self, level: int):
        self.level = level
        self.console = console
        # pass

    def log(self, level: int, msg: Any, style: str | None = None) -> None:
        if self.level <= level:
            level_name = f"{logging.getLevelName(level)}"
            level_name = f"{level_name:<10}"
            color = self.style_map[level]
            if color:
                level_name = f"[{color}]{level_name}[/{color}]"
                msg = level_name + str(msg)
            self.console.log(msg, style=style)

    def info(self, msg: Any, style: str | None =None) -> None:
        self.log(logging.INFO, msg, style)

    def debug(self, msg: Any, style: str | None =None) -> None:
        self.log(logging.DEBUG, msg, style)

    def warning(self, msg: Any, style: str | None =None) -> None:
        self.log(logging.WARNING, msg, style)

    def error(self, msg: Any, style: str | None =None) -> None:
        self.log(logging.ERROR, msg, style)
        
console = Console()
logger = SceneryLogger(logging.INFO)




# NOTE mad: do not erase

# def show_root_logger_config():
#     """Show detailed configuration of the root logger only."""
#     root = logging.getLogger()
    
#     print("🌳 ROOT LOGGER CONFIGURATION")
#     print("=" * 50)
#     print(f"Name: '{root.name}' (empty = root)")
#     print(f"Level: {logging.getLevelName(root.level)} ({root.level})")
#     print(f"Effective Level: {logging.getLevelName(root.getEffectiveLevel())}")
#     print(f"Propagate: {root.propagate}")
#     print(f"Disabled: {root.disabled}")
#     print(f"Number of Handlers: {len(root.handlers)}")
    
#     if root.handlers:
#         print(f"\n📋 HANDLERS:")
#         for i, handler in enumerate(root.handlers):
#             print(f"  [{i}] {type(handler).__name__}")
#             print(f"      Level: {logging.getLevelName(handler.level)} ({handler.level})")
            
#             # Formatter info
#             if hasattr(handler, 'formatter') and handler.formatter:
#                 fmt = handler.formatter
#                 print(f"      Format: '{fmt._fmt}'")
#                 print(f"      Date Format: '{fmt.datefmt}'")
#             else:
#                 print(f"      Formatter: None")
            
#             # Stream info for StreamHandler
#             if hasattr(handler, 'stream'):
#                 stream_name = getattr(handler.stream, 'name', str(handler.stream))
#                 print(f"      Stream: {stream_name}")
            
#             # File info for FileHandler
#             elif hasattr(handler, 'baseFilename'):
#                 print(f"      File: {handler.baseFilename}")
            
#             # Rich-specific info
#             if 'Rich' in type(handler).__name__:
#                 print(f"      Rich Tracebacks: {getattr(handler, 'rich_tracebacks', 'N/A')}")
#                 print(f"      Markup: {getattr(handler, 'markup', 'N/A')}")
#                 if hasattr(handler, 'console') and handler.console:
#                     print(f"      Console File: {getattr(handler.console, 'file', 'N/A')}")
#     else:
#         print("\n📋 No handlers configured")
