"""
SSH 连接配置数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import os


class AuthType(Enum):
    """认证类型枚举"""
    PASSWORD = "password"
    KEY = "key"
    AGENT = "agent"


@dataclass
class SSHAuthConfig:
    """SSH 认证配置"""
    
    auth_type: AuthType = AuthType.KEY
    username: str = "root"
    password: Optional[str] = None
    key_path: Optional[str] = None
    key_data: Optional[str] = None
    passphrase: Optional[str] = None
    
    def validate(self) -> None:
        """验证认证配置"""
        if self.auth_type == AuthType.PASSWORD:
            if not self.password:
                raise ValueError("密码认证需要提供 password")
        elif self.auth_type == AuthType.KEY:
            if not (self.key_path or self.key_data):
                raise ValueError("密钥认证需要提供 key_path 或 key_data")
            if self.key_path and not os.path.exists(self.key_path):
                raise FileNotFoundError(f"密钥文件不存在: {self.key_path}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（隐藏敏感信息）"""
        result = {
            "auth_type": self.auth_type.value,
            "username": self.username,
        }
        if self.password:
            result["password"] = "***"
        if self.key_path:
            result["key_path"] = self.key_path
        if self.key_data:
            result["key_data"] = "***"
        if self.passphrase:
            result["passphrase"] = "***"
        return result


@dataclass
class SSHConnectionConfig:
    """SSH 连接配置"""
    
    host: str
    port: int = 22
    auth: SSHAuthConfig = field(default_factory=SSHAuthConfig)
    timeout: int = 30
    connect_timeout: int = 10
    keepalive_interval: int = 30
    keepalive_count_max: int = 3
    compress: bool = False
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    def validate(self) -> None:
        """验证连接配置"""
        if not self.host:
            raise ValueError("主机地址不能为空")
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"端口号无效: {self.port}")
        if self.timeout <= 0:
            raise ValueError(f"超时时间必须大于0: {self.timeout}")
        if self.connect_timeout <= 0:
            raise ValueError(f"连接超时必须大于0: {self.connect_timeout}")
        
        # 验证认证配置
        self.auth.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "auth": self.auth.to_dict(),
            "timeout": self.timeout,
            "connect_timeout": self.connect_timeout,
            "keepalive_interval": self.keepalive_interval,
            "keepalive_count_max": self.keepalive_count_max,
            "compress": self.compress,
            "description": self.description,
            "tags": self.tags,
        }
    
    @property
    def connection_string(self) -> str:
        """获取连接字符串"""
        return f"{self.auth.username}@{self.host}:{self.port}"
    
    @property
    def unique_id(self) -> str:
        """获取唯一标识符"""
        import hashlib
        import json
        config_dict = self.to_dict()
        # 移除可能变化的字段
        config_dict.pop("description", None)
        config_dict.pop("tags", None)
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()


class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class CommandResult:
    """命令执行结果"""
    
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": round(self.execution_time, 3),
            "success": self.success,
            "error_message": self.error_message,
            "cached": self.cached,
        }
    
    @property
    def output(self) -> str:
        """获取完整输出"""
        if self.stderr:
            return f"{self.stdout}\n{self.stderr}"
        return self.stdout
    
    def raise_if_error(self) -> None:
        """如果有错误则抛出异常"""
        if not self.success:
            error_msg = self.error_message or f"命令执行失败: {self.command}"
            raise RuntimeError(f"{error_msg}\nExit code: {self.exit_code}\nStderr: {self.stderr}")
