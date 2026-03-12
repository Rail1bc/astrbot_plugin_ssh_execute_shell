"""
SSH执行器核心模块
"""

from .connection import (
    SSHConnection,
    SSHConnectionManager,
    get_global_manager,
    shutdown_global_manager,
)

from .executor import (
    SSHCommandExecutor,
    get_global_executor,
    shutdown_global_executor,
)

__all__ = [
    # Connection
    "SSHConnection",
    "SSHConnectionManager",
    "get_global_manager",
    "shutdown_global_manager",
    
    # Executor
    "SSHCommandExecutor",
    "get_global_executor",
    "shutdown_global_executor",
]
