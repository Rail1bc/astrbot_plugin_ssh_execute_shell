"""
SSH 执行器包
"""

# 不进行通配符导入，避免导入问题
# from .core import *
# from .models import *
# from .exceptions import *

# 显式导入核心类
from ssh_executor.core.connection import SSHConnection, SSHConnectionManager, get_global_manager, shutdown_global_manager
from ssh_executor.core.executor import SSHCommandExecutor, get_global_executor, shutdown_global_executor
from ssh_executor.models.config import (
    SSHConnectionConfig, 
    SSHAuthConfig, 
    AuthType, 
    ConnectionStatus, 
    CommandResult
)
from ssh_executor.exceptions import (
    SSHExecutorError,
    SSHConnectionError,
    SSHAuthenticationError,
    SSHTimeoutError,
    SSHCommandError,
    SSHConfigError,
    SSHConnectionPoolError,
    SSHKeyError,
    SSHPermissionError,
    SSHNetworkError,
    SSHRetryExhaustedError,
    SSHHostKeyError,
    SSHCommandTimeoutError,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "SSHConnection",
    "SSHConnectionManager",
    "SSHCommandExecutor",
    "get_global_executor",
    "shutdown_global_executor",
    "get_global_manager",
    "shutdown_global_manager",
    
    # Models
    "SSHConnectionConfig",
    "SSHAuthConfig",
    "AuthType",
    "ConnectionStatus",
    "CommandResult",
    
    # Exceptions
    "SSHExecutorError",
    "SSHConnectionError",
    "SSHAuthenticationError",
    "SSHTimeoutError",
    "SSHCommandError",
    "SSHConfigError",
    "SSHConnectionPoolError",
    "SSHKeyError",
    "SSHPermissionError",
    "SSHNetworkError",
    "SSHRetryExhaustedError",
    "SSHHostKeyError",
    "SSHCommandTimeoutError",
]
