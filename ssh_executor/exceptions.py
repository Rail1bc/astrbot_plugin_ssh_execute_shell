"""
SSH 执行器自定义异常类
"""

class SSHExecutorError(Exception):
    """SSH 执行器基础异常"""
    pass


class SSHConnectionError(SSHExecutorError):
    """SSH 连接异常"""
    pass


class SSHAuthenticationError(SSHConnectionError):
    """SSH 认证异常"""
    pass


class SSHTimeoutError(SSHConnectionError):
    """SSH 超时异常"""
    pass


class SSHCommandError(SSHExecutorError):
    """SSH 命令执行异常"""
    pass


class SSHConfigError(SSHExecutorError):
    """SSH 配置异常"""
    pass


class SSHConnectionPoolError(SSHExecutorError):
    """SSH 连接池异常"""
    pass


class SSHKeyError(SSHAuthenticationError):
    """SSH 密钥异常"""
    pass


class SSHPermissionError(SSHAuthenticationError):
    """SSH 权限异常"""
    pass


class SSHNetworkError(SSHConnectionError):
    """SSH 网络异常"""
    pass


class SSHRetryExhaustedError(SSHConnectionError):
    """SSH 重试耗尽异常"""
    pass


class SSHHostKeyError(SSHConnectionError):
    """SSH 主机密钥异常"""
    pass


class SSHCommandTimeoutError(SSHCommandError):
    """SSH 命令超时异常"""
    pass
