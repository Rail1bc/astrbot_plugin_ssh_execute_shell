"""
SSH 连接管理类
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import asyncssh

from ..models.config import SSHConnectionConfig, ConnectionStatus, CommandResult
from ..exceptions import SSHConnectionError, SSHAuthenticationError, SSHTimeoutError

logger = logging.getLogger(__name__)


class SSHConnection:
    """单个 SSH 连接封装"""
    
    def __init__(self, config: SSHConnectionConfig):
        self.config = config
        self.connection: Optional[asyncssh.SSHClientConnection] = None
        self.status = ConnectionStatus.DISCONNECTED
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.error_count = 0
        self.connection_id = f"conn_{config.unique_id}_{self.created_at.timestamp():.0f}"
        
    async def connect(self) -> None:
        """建立 SSH 连接"""
        if self.status == ConnectionStatus.CONNECTED:
            return
            
        self.status = ConnectionStatus.CONNECTING
        logger.info(f"正在建立 SSH 连接: {self.config.connection_string}")
        
        try:
            auth_methods = await self._get_auth_methods()
            
            self.connection = await asyncio.wait_for(
                asyncssh.connect(
                    host=self.config.host,
                    port=self.config.port,
                    username=self.config.auth.username,
                    client_keys=self._get_client_keys(),
                    password=self.config.auth.password,
                    known_hosts=None,  # 暂时不验证 known_hosts
                    keepalive_interval=self.config.keepalive_interval,
                    keepalive_count_max=self.config.keepalive_count_max,
                    compress=self.config.compress,
                    **auth_methods
                ),
                timeout=self.config.connect_timeout
            )
            
            self.status = ConnectionStatus.CONNECTED
            self.error_count = 0
            logger.info(f"SSH 连接建立成功: {self.config.connection_string}")
            
        except asyncio.TimeoutError:
            error_msg = f"连接超时: {self.config.connection_string}"
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            logger.error(error_msg)
            raise SSHTimeoutError(error_msg)
            
        except asyncssh.PermissionDenied:
            error_msg = f"认证失败: {self.config.connection_string}"
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            logger.error(error_msg)
            raise SSHAuthenticationError(error_msg)
            
        except Exception as e:
            error_msg = f"连接失败: {self.config.connection_string} - {str(e)}"
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            logger.error(error_msg)
            raise SSHConnectionError(error_msg)
    
    async def _get_auth_methods(self) -> Dict[str, Any]:
        """获取认证方法"""
        auth_methods = {}
        
        if self.config.auth.auth_type.value == "key":
            if self.config.auth.key_data:
                auth_methods["client_keys"] = [self.config.auth.key_data]
            elif self.config.auth.key_path:
                # asyncssh 会自动处理 key_path
                pass
        elif self.config.auth.auth_type.value == "password":
            if self.config.auth.password:
                auth_methods["password"] = self.config.auth.password
        
        return auth_methods
    
    def _get_client_keys(self) -> Optional[list]:
        """获取客户端密钥"""
        if self.config.auth.auth_type.value == "key" and self.config.auth.key_path:
            return [self.config.auth.key_path]
        return None
    
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """执行命令"""
        if self.status != ConnectionStatus.CONNECTED or not self.connection:
            raise SSHConnectionError("连接未建立或已关闭")
        
        start_time = datetime.now()
        result = CommandResult(command=command)
        
        try:
            actual_timeout = timeout or self.config.timeout
            
            async with asyncio.timeout(actual_timeout):
                # 执行命令
                process = await self.connection.create_process(command)
                
                # 读取输出
                stdout = await process.stdout.read()
                stderr = await process.stderr.read()
                
                # 等待进程结束
                exit_code = await process.wait()
                
                result.stdout = stdout.decode('utf-8', errors='replace') if stdout else ""
                result.stderr = stderr.decode('utf-8', errors='replace') if stderr else ""
                result.exit_code = exit_code
                result.success = exit_code == 0
                result.execution_time = (datetime.now() - start_time).total_seconds()
                
                if exit_code != 0 and not result.stderr:
                    result.stderr = f"命令执行失败，退出码: {exit_code}"
                
        except asyncio.TimeoutError:
            result.success = False
            result.error_message = f"命令执行超时: {command}"
            result.execution_time = (datetime.now() - start_time).total_seconds()
            logger.warning(f"命令执行超时: {command}")
            
        except Exception as e:
            result.success = False
            result.error_message = f"命令执行失败: {str(e)}"
            result.execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"命令执行失败: {command} - {str(e)}")
        
        self.last_used_at = datetime.now()
        return result
    
    async def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            result = await self.execute_command("echo 'connection_test'", timeout=5)
            return result.success and "connection_test" in result.stdout.strip()
        except Exception:
            return False
    
    async def close(self) -> None:
        """关闭连接"""
        if self.connection:
            try:
                self.connection.close()
                await self.connection.wait_closed()
                logger.info(f"SSH 连接已关闭: {self.config.connection_string}")
            except Exception as e:
                logger.warning(f"关闭连接时出错: {self.config.connection_string} - {str(e)}")
            finally:
                self.connection = None
                self.status = ConnectionStatus.CLOSED
    
    def is_expired(self, max_age_minutes: int = 30) -> bool:
        """检查连接是否过期"""
        age = datetime.now() - self.last_used_at
        return age > timedelta(minutes=max_age_minutes)
    
    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        return (
            self.status == ConnectionStatus.CONNECTED and 
            self.connection is not None and
            self.error_count < 3
        )


class SSHConnectionManager:
    """SSH 连接管理器，支持连接池"""
    
    def __init__(self, max_pool_size: int = 10, connection_timeout: int = 30):
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        self.connections: Dict[str, SSHConnection] = {}
        self._lock = asyncio.Lock()
        
    async def get_connection(self, config: SSHConnectionConfig) -> SSHConnection:
        """获取 SSH 连接（从池中获取或新建）"""
        connection_id = config.unique_id
        
        async with self._lock:
            # 检查是否已有连接
            if connection_id in self.connections:
                conn = self.connections[connection_id]
                
                # 检查连接是否健康
                if conn.is_healthy() and not conn.is_expired():
                    logger.debug(f"复用现有连接: {config.connection_string}")
                    return conn
                else:
                    # 关闭不健康的连接
                    logger.debug(f"关闭不健康的连接: {config.connection_string}")
                    await conn.close()
                    del self.connections[connection_id]
            
            # 创建新连接
            if len(self.connections) >= self.max_pool_size:
                await self._cleanup_old_connections()
            
            conn = SSHConnection(config)
            await conn.connect()
            self.connections[connection_id] = conn
            
            logger.info(f"创建新连接: {config.connection_string}")
            return conn
    
    async def _cleanup_old_connections(self) -> None:
        """清理旧的连接"""
        to_remove = []
        
        for conn_id, conn in self.connections.items():
            if conn.is_expired() or not conn.is_healthy():
                to_remove.append(conn_id)
        
        for conn_id in to_remove:
            conn = self.connections[conn_id]
            await conn.close()
            del self.connections[conn_id]
            logger.debug(f"清理连接: {conn.config.connection_string}")
    
    async def execute_command(
        self, 
        config: SSHConnectionConfig, 
        command: str, 
        timeout: Optional[int] = None
    ) -> CommandResult:
        """执行命令（自动管理连接）"""
        conn = await self.get_connection(config)
        
        try:
            result = await conn.execute_command(command, timeout)
            return result
        except Exception as e:
            # 如果执行失败，标记连接为不健康
            conn.error_count += 1
            conn.status = ConnectionStatus.ERROR
            raise
    
    async def test_connection(self, config: SSHConnectionConfig) -> bool:
        """测试连接是否正常"""
        try:
            conn = await self.get_connection(config)
            return await conn.test_connection()
        except Exception:
            return False
    
    async def close_all(self) -> None:
        """关闭所有连接"""
        async with self._lock:
            for conn in self.connections.values():
                await conn.close()
            self.connections.clear()
            logger.info("所有 SSH 连接已关闭")
    
    @asynccontextmanager
    async def connection_context(self, config: SSHConnectionConfig):
        """异步上下文管理器"""
        conn = None
        try:
            conn = await self.get_connection(config)
            yield conn
        finally:
            if conn:
                # 在上下文管理器中不自动关闭连接，由连接池管理
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        total = len(self.connections)
        healthy = sum(1 for conn in self.connections.values() if conn.is_healthy())
        expired = sum(1 for conn in self.connections.values() if conn.is_expired())
        
        return {
            "total_connections": total,
            "healthy_connections": healthy,
            "expired_connections": expired,
            "max_pool_size": self.max_pool_size,
            "connection_ids": list(self.connections.keys())
        }


# 全局连接管理器实例
_global_manager: Optional[SSHConnectionManager] = None


def get_global_manager() -> SSHConnectionManager:
    """获取全局连接管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = SSHConnectionManager()
    return _global_manager


async def shutdown_global_manager() -> None:
    """关闭全局连接管理器"""
    global _global_manager
    if _global_manager:
        await _global_manager.close_all()
        _global_manager = None
