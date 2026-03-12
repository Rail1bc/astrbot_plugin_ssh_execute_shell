#!/usr/bin/env python3
"""
SSH Execute Shell 插件原型代码
演示如何实现透明化的远程命令执行
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 假设的 SSH 库导入
try:
    import asyncssh
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
    print("警告: asyncssh 未安装，SSH 功能将不可用")

class AuthType(Enum):
    """认证类型"""
    PASSWORD = "password"
    KEY = "key"
    AGENT = "agent"

@dataclass
class SSHConnectionConfig:
    """SSH 连接配置"""
    host: str
    port: int = 22
    username: str = "root"
    auth_type: AuthType = AuthType.KEY
    key_path: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "auth_type": self.auth_type.value,
            "key_path": self.key_path,
            "password": "***" if self.password else None,
            "timeout": self.timeout
        }

@dataclass
class CommandResult:
    """命令执行结果"""
    command: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float  # 执行时间（秒）
    cached: bool = False  # 是否来自缓存
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": round(self.execution_time, 3),
            "cached": self.cached
        }

class SSHConnectionPool:
    """SSH 连接池（简化版）"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.connections: Dict[str, asyncssh.Connection] = {}
        self.connection_configs: Dict[str, SSHConnectionConfig] = {}
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "connection_errors": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def get_connection(self, config: SSHConnectionConfig) -> asyncssh.Connection:
        """获取或创建 SSH 连接"""
        connection_key = f"{config.username}@{config.host}:{config.port}"
        
        # 检查现有连接
        if connection_key in self.connections:
            conn = self.connections[connection_key]
            try:
                # 简单检查连接是否仍然有效
                await conn.run("echo 'ping'", timeout=5)
                return conn
            except:
                # 连接已失效，移除并重新创建
                del self.connections[connection_key]
        
        # 创建新连接
        try:
            start_time = time.time()
            
            if config.auth_type == AuthType.KEY:
                conn = await asyncssh.connect(
                    config.host,
                    port=config.port,
                    username=config.username,
                    client_keys=[config.key_path] if config.key_path else None,
                    known_hosts=None,  # 简化：不验证主机密钥
                    timeout=config.timeout
                )
            elif config.auth_type == AuthType.PASSWORD:
                conn = await asyncssh.connect(
                    config.host,
                    port=config.port,
                    username=config.username,
                    password=config.password,
                    known_hosts=None,
                    timeout=config.timeout
                )
            else:
                raise ValueError(f"不支持的认证类型: {config.auth_type}")
            
            self.connections[connection_key] = conn
            self.connection_configs[connection_key] = config
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.connections)
            
            connect_time = time.time() - start_time
            print(f"✅ SSH连接建立成功: {connection_key} (耗时: {connect_time:.2f}s)")
            
            return conn
            
        except Exception as e:
            self.stats["connection_errors"] += 1
            print(f"❌ SSH连接失败 {connection_key}: {e}")
            raise
    
    async def execute_command(self, config: SSHConnectionConfig, command: str) -> CommandResult:
        """执行远程命令"""
        start_time = time.time()
        
        try:
            # 获取连接
            conn = await self.get_connection(config)
            
            # 执行命令
            result = await conn.run(command, timeout=config.timeout)
            
            execution_time = time.time() - start_time
            
            return CommandResult(
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_status,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"命令执行超时 ({config.timeout}s)",
                exit_code=255,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"执行错误: {e}",
                exit_code=255,
                execution_time=execution_time
            )
    
    async def batch_execute(self, config: SSHConnectionConfig, commands: List[str]) -> List[CommandResult]:
        """批量执行命令"""
        results = []
        conn = await self.get_connection(config)
        
        for command in commands:
            start_time = time.time()
            try:
                result = await conn.run(command, timeout=config.timeout)
                execution_time = time.time() - start_time
                
                results.append(CommandResult(
                    command=command,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_status,
                    execution_time=execution_time
                ))
            except Exception as e:
                execution_time = time.time() - start_time
                results.append(CommandResult(
                    command=command,
                    stdout="",
                    stderr=f"执行错误: {e}",
                    exit_code=255,
                    execution_time=execution_time
                ))
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "connection_count": len(self.connections),
            "config_count": len(self.connection_configs)
        }

class ResultCache:
    """结果缓存（简化版）"""
    
    def __init__(self, ttl: int = 60):
        self.cache: Dict[str, tuple[CommandResult, float]] = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[CommandResult]:
        """获取缓存结果"""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                result.cached = True
                return result
            else:
                # 缓存过期
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, result: CommandResult):
        """设置缓存"""
        self.cache[key] = (result, time.time())
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        return {
            "cache_size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}"
        }

class SSHExecutor:
    """SSH 执行器（主类）"""
    
    def __init__(self):
        self.connection_pool = SSHConnectionPool()
        self.cache = ResultCache(ttl=60)
        self.command_history: List[Dict] = []
    
    def _get_cache_key(self, config: SSHConnectionConfig, command: str) -> str:
        """生成缓存键"""
        import hashlib
        config_dict = config.to_dict()
        config_dict.pop("password", None)  # 密码不参与缓存键
        data = f"{json.dumps(config_dict, sort_keys=True)}|{command}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def execute(self, config: SSHConnectionConfig, command: str, use_cache: bool = True) -> CommandResult:
        """执行命令（带缓存）"""
        
        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(config, command)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                print(f"📦 缓存命中: {command[:50]}...")
                return cached_result
        
        # 执行远程命令
        print(f"🚀 执行远程命令: {command[:50]}...")
        result = await self.connection_pool.execute_command(config, command)
        
        # 缓存结果（如果执行成功）
        if use_cache and result.exit_code == 0:
            cache_key = self._get_cache_key(config, command)
            self.cache.set(cache_key, result)
        
        # 记录历史
        self.command_history.append({
            "timestamp": time.time(),
            "config": config.to_dict(),
            "command": command,
            "result": result.to_dict()
        })
        
        return result
    
    async def batch_execute(self, config: SSHConnectionConfig, commands: List[str]) -> List[CommandResult]:
        """批量执行命令"""
        print(f"🚀 批量执行 {len(commands)} 个命令")
        return await self.connection_pool.batch_execute(config, commands)
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        pool_stats = self.connection_pool.get_stats()
        cache_stats = self.cache.get_stats()
        
        # 计算平均执行时间
        if self.command_history:
            avg_time = sum(r["result"]["execution_time"] for r in self.command_history) / len(self.command_history)
        else:
            avg_time = 0
        
        return {
            "connection_pool": pool_stats,
            "cache": cache_stats,
            "command_history_count": len(self.command_history),
            "average_execution_time": round(avg_time, 3),
            "total_commands_executed": len(self.command_history)
        }

# 演示代码
async def demo():
    """演示 SSH 执行器的使用"""
    
    if not SSH_AVAILABLE:
        print("❌ 请先安装 asyncssh: pip install asyncssh")
        return
    
    print("=" * 50)
    print("SSH Execute Shell 插件原型演示")
    print("=" * 50)
    
    # 创建配置
    config = SSHConnectionConfig(
        host="117.72.179.121",
        username="root",
        auth_type=AuthType.PASSWORD,  # 实际使用时应该使用密钥
        timeout=10
    )
    
    # 创建执行器
    executor = SSHExecutor()
    
    # 演示1: 执行单个命令
    print("\n1. 执行单个命令:")
    result = await executor.execute(config, "uname -a")
    print(f"   命令: {result.command}")
    print(f"   输出: {result.stdout.strip()}")
    print(f"   耗时: {result.execution_time:.2f}s")
    print(f"   退出码: {result.exit_code}")
    
    # 演示2: 执行系统信息命令
    print("\n2. 获取系统信息:")
    commands = [
        "uptime",
        "df -h",
        "free -h"
    ]
    
    for cmd in commands:
        result = await executor.execute(config, cmd)
        print(f"   {cmd}: {result.stdout.strip()[:50]}...")
    
    # 演示3: 批量执行
    print("\n3. 批量执行测试:")
    batch_results = await executor.batch_execute(config, [
        "echo '批量命令1'",
        "echo '批量命令2'",
        "echo '批量命令3'"
    ])
    
    for i, result in enumerate(batch_results, 1):
        print(f"   命令{i}: {result.stdout.strip()} (耗时: {result.execution_time:.2f}s)")
    
    # 演示4: 缓存效果
    print("\n4. 缓存效果测试:")
    
    # 第一次执行（缓存未命中）
    start = time.time()
    result1 = await executor.execute(config, "date", use_cache=True)
    time1 = time.time() - start
    
    # 第二次执行（应该命中缓存）
    start = time.time()
    result2 = await executor.execute(config, "date", use_cache=True)
    time2 = time.time() - start
    
    print(f"   第一次执行: {time1:.3f}s (缓存: {result1.cached})")
    print(f"   第二次执行: {time2:.3f}s (缓存: {result2.cached})")
    print(f"   性能提升: {((time1 - time2) / time1 * 100):.1f}%")
    
    # 显示统计信息
    print("\n5. 性能统计:")
    stats = executor.get_performance_stats()
    for category, data in stats.items():
        if isinstance(data, dict):
            print(f"   {category}:")
            for key, value in data.items():
                print(f"     {key}: {value}")
        else:
            print(f"   {category}: {data}")
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)

if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo())
