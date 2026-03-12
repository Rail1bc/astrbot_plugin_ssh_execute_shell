"""
SSH 执行器核心模块
"""

from .connection import (
    SSHConnection,
    SSHConnectionManager,
    get_global_manager,
    shutdown_global_manager,
)

__all__ = [
    "SSHConnection",
    "SSHConnectionManager", 
    "get_global_manager",
    "shutdown_global_manager",
]
