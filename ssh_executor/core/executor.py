"""
SSH命令执行器模块
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, List
from datetime import datetime

from ..exceptions import (
    SSHCommandError,
    SSHTimeoutError,
    SSHCommandTimeoutError
)
from ..models.config import CommandResult, SSHConnectionConfig, SSHAuthConfig
from .connection import SSHConnectionManager

logger = logging.getLogger(__name__)


class SSHCommandExecutor:
    """SSH命令执行器"""
    
    def __init__(
        self,
        connection_manager: Optional[SSHConnectionManager] = None,
        default_timeout: int = 30,
        default_encoding: str = "utf-8"
    ):
        """
        初始化SSH命令执行器
        
        Args:
            connection_manager: SSH连接管理器实例
            default_timeout: 默认命令超时时间（秒）
            default_encoding: 默认编码格式
        """
        self.connection_manager = connection_manager or SSHConnectionManager()
        self.default_timeout = default_timeout
        self.default_encoding = default_encoding
        self._execution_stats: Dict[str, Any] = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "last_execution_time": None,
        }
        
        logger.info(f"SSHCommandExecutor initialized with default_timeout={default_timeout}s")
    
    async def execute(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        command: str = "",
        auth_config: Optional[SSHAuthConfig] = None,
        connection_config: Optional[SSHConnectionConfig] = None,
        timeout: Optional[int] = None,
        encoding: Optional[str] = None,
        workdir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        use_sudo: bool = False,
        sudo_password: Optional[str] = None,
        capture_output: bool = True,
        **kwargs
    ) -> CommandResult:
        """
        执行SSH命令
        
        Args:
            host: 主机地址
            port: SSH端口
            username: 用户名
            command: 要执行的命令
            auth_config: 认证配置
            connection_config: 连接配置
            timeout: 命令超时时间
            encoding: 输出编码
            workdir: 工作目录
            env: 环境变量
            use_sudo: 是否使用sudo
            sudo_password: sudo密码
            capture_output: 是否捕获输出
            **kwargs: 其他参数
            
        Returns:
            CommandResult: 命令执行结果
            
        Raises:
            SSHCommandError: 命令执行错误
            SSHTimeoutError: 命令超时错误
        """
        start_time = datetime.now()
        command_id = f"{host}:{port}:{username}:{start_time.timestamp()}"
        
        logger.debug(f"Executing command [{command_id}]: {command}")
        
        # 使用默认值
        timeout = timeout or self.default_timeout
        encoding = encoding or self.default_encoding
        
        # 构建完整命令
        full_command = self._build_command(
            command, 
            workdir=workdir, 
            env=env, 
            use_sudo=use_sudo,
            sudo_password=sudo_password
        )
        
        try:
            # 获取连接
            connection = await self.connection_manager.get_connection(
                host=host,
                port=port,
                username=username,
                auth_config=auth_config,
                connection_config=connection_config,
                **kwargs
            )
            
            # 执行命令
            try:
                result = await asyncio.wait_for(
                    self._execute_command(
                        connection, 
                        full_command, 
                        encoding=encoding,
                        capture_output=capture_output
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise SSHCommandTimeoutError(
                    f"Command timeout after {timeout} seconds: {command}"
                )
            
            # 更新统计信息
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(execution_time, result.exit_code == 0)
            
            logger.info(
                f"Command executed successfully [{command_id}]: "
                f"exit_code={result.exit_code}, "
                f"time={execution_time:.3f}s"
            )
            
            return result
            
        except Exception as e:
            # 更新失败统计
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(execution_time, False)
            
            logger.error(
                f"Command execution failed [{command_id}]: {str(e)}"
            )
            
            if isinstance(e, (SSHCommandError, SSHTimeoutError)):
                raise e
            else:
                raise SSHCommandError(f"Command execution failed: {str(e)}")
    
    async def async_execute(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        command: str = "",
        auth_config: Optional[SSHAuthConfig] = None,
        connection_config: Optional[SSHConnectionConfig] = None,
        timeout: Optional[int] = None,
        encoding: Optional[str] = None,
        workdir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        use_sudo: bool = False,
        sudo_password: Optional[str] = None,
        capture_output: bool = True,
        **kwargs
    ) -> CommandResult:
        """
        异步执行SSH命令（与execute方法相同，提供异步接口）
        """
        return await self.execute(
            host=host,
            port=port,
            username=username,
            command=command,
            auth_config=auth_config,
            connection_config=connection_config,
            timeout=timeout,
            encoding=encoding,
            workdir=workdir,
            env=env,
            use_sudo=use_sudo,
            sudo_password=sudo_password,
            capture_output=capture_output,
            **kwargs
        )
    
    async def execute_multi(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        commands: List[str] = [],
        auth_config: Optional[SSHAuthConfig] = None,
        connection_config: Optional[SSHConnectionConfig] = None,
        timeout: Optional[int] = None,
        encoding: Optional[str] = None,
        workdir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        use_sudo: bool = False,
        sudo_password: Optional[str] = None,
        capture_output: bool = True,
        stop_on_error: bool = True,
        **kwargs
    ) -> List[CommandResult]:
        """
        批量执行多个命令
        
        Args:
            commands: 命令列表
            stop_on_error: 遇到错误时是否停止执行
            
        Returns:
            List[CommandResult]: 命令执行结果列表
        """
        results = []
        
        for i, command in enumerate(commands):
            try:
                result = await self.execute(
                    host=host,
                    port=port,
                    username=username,
                    command=command,
                    auth_config=auth_config,
                    connection_config=connection_config,
                    timeout=timeout,
                    encoding=encoding,
                    workdir=workdir,
                    env=env,
                    use_sudo=use_sudo,
                    sudo_password=sudo_password,
                    capture_output=capture_output,
                    **kwargs
                )
                results.append(result)
                
                # 如果命令失败且设置了停止，则中断
                if stop_on_error and result.exit_code != 0:
                    logger.warning(
                        f"Command {i+1}/{len(commands)} failed with exit_code={result.exit_code}, "
                        f"stopping execution as stop_on_error=True"
                    )
                    break
                    
            except Exception as e:
                logger.error(f"Command {i+1}/{len(commands)} execution failed: {str(e)}")
                if stop_on_error:
                    raise
        
        return results
    
    async def _execute_command(
        self,
        connection,
        command: str,
        encoding: str = "utf-8",
        capture_output: bool = True
    ) -> CommandResult:
        """
        执行单个命令
        
        Args:
            connection: SSH连接对象
            command: 要执行的命令
            encoding: 输出编码
            capture_output: 是否捕获输出
            
        Returns:
            CommandResult: 命令执行结果
        """
        stdout_data = []
        stderr_data = []
        exit_code = 0
        
        try:
            if capture_output:
                # 执行命令并捕获输出
                result = await connection.run(
                    command,
                    encoding=encoding,
                    check=False  # 不检查退出码，我们自己处理
                )
                
                stdout_data = result.stdout.splitlines() if result.stdout else []
                stderr_data = result.stderr.splitlines() if result.stderr else []
                exit_code = result.exit_status
            else:
                # 执行命令但不捕获输出
                result = await connection.run(
                    command,
                    encoding=encoding,
                    check=False
                )
                exit_code = result.exit_status
            
            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_data,
                stderr=stderr_data,
                success=exit_code == 0,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Command execution error: {str(e)}")
            raise SSHCommandError(f"Command execution failed: {str(e)}")
    
    def _build_command(
        self,
        command: str,
        workdir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        use_sudo: bool = False,
        sudo_password: Optional[str] = None
    ) -> str:
        """
        构建完整的命令字符串
        
        Args:
            command: 原始命令
            workdir: 工作目录
            env: 环境变量
            use_sudo: 是否使用sudo
            sudo_password: sudo密码
            
        Returns:
            str: 构建后的完整命令
        """
        parts = []
        
        # 添加环境变量
        if env:
            env_vars = " ".join([f"{k}='{v}'" for k, v in env.items()])
            parts.append(env_vars)
        
        # 添加工作目录
        if workdir:
            parts.append(f"cd {workdir} &&")
        
        # 添加sudo
        if use_sudo:
            if sudo_password:
                # 使用echo传递密码（注意：这不安全，仅用于演示）
                parts.append(f"echo '{sudo_password}' | sudo -S")
            else:
                parts.append("sudo")
        
        # 添加原始命令
        parts.append(command)
        
        return " ".join(parts)
    
    def _update_stats(self, execution_time: float, success: bool):
        """更新执行统计信息"""
        self._execution_stats["total_commands"] += 1
        self._execution_stats["total_execution_time"] += execution_time
        
        if success:
            self._execution_stats["successful_commands"] += 1
        else:
            self._execution_stats["failed_commands"] += 1
        
        # 计算平均执行时间
        if self._execution_stats["total_commands"] > 0:
            self._execution_stats["average_execution_time"] = (
                self._execution_stats["total_execution_time"] / 
                self._execution_stats["total_commands"]
            )
        
        self._execution_stats["last_execution_time"] = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self._execution_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._execution_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "last_execution_time": None,
        }
    
    async def close(self):
        """关闭执行器"""
        await self.connection_manager.close()
        logger.info("SSHCommandExecutor closed")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 全局执行器实例
_global_executor: Optional[SSHCommandExecutor] = None


def get_global_executor() -> SSHCommandExecutor:
    """获取全局SSH命令执行器实例"""
    global _global_executor
    if _global_executor is None:
        _global_executor = SSHCommandExecutor()
    return _global_executor


async def shutdown_global_executor():
    """关闭全局SSH命令执行器"""
    global _global_executor
    if _global_executor is not None:
        await _global_executor.close()
        _global_executor = None
        logger.info("Global SSHCommandExecutor shutdown")
