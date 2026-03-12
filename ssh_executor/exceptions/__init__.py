"""
SSH 执行器异常模块
"""

from .exceptions import (
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

__all__ = [
    'SSHExecutorError',
    'SSHConnectionError',
    'SSHAuthenticationError',
    'SSHTimeoutError',
    'SSHCommandError',
    'SSHConfigError',
    'SSHConnectionPoolError',
    'SSHKeyError',
    'SSHPermissionError',
    'SSHNetworkError',
    'SSHRetryExhaustedError',
    'SSHHostKeyError',
    'SSHCommandTimeoutError',
]
