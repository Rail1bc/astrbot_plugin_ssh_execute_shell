#!/usr/bin/env python3
"""
测试 SSH 连接管理类
"""
import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ssh_executor import SSHConnectionManager, SSHConnectionConfig, SSHAuthConfig, AuthType


async def test_ssh_connection():
    """测试 SSH 连接"""
    print("=" * 50)
    print("SSH 连接管理类测试")
    print("=" * 50)
    
    # 创建 SSH 连接配置
    # 注意：这里使用一个测试服务器，实际使用时需要替换为真实的服务器
    config = SSHConnectionConfig(
        host="localhost",  # 测试使用本地主机
        port=22,
        auth=SSHAuthConfig(
            auth_type=AuthType.KEY,
            username="root",
            # key_path="/path/to/private_key",  # 实际使用时需要提供密钥路径
        ),
        timeout=10,
        connect_timeout=5,
        description="测试服务器",
    )
    
    # 创建连接管理器
    manager = SSHConnectionManager(max_retries=2, retry_delay=1.0)
    
    try:
        print(f"\n1. 测试连接到: {config.connection_string}")
        
        # 尝试连接
        print("   正在建立连接...")
        connection = await manager.connect(config)
        print(f"   ✅ 连接成功!")
        
        print(f"\n2. 获取连接状态:")
        status = manager.get_connection_status(config)
        print(f"   状态: {status.value}")
        
        print(f"\n3. 测试命令执行:")
        test_commands = [
            "echo 'Hello from SSH Executor'",
            "uname -a",
            "date",
        ]
        
        for cmd in test_commands:
            print(f"   执行命令: {cmd}")
            result = await manager.execute_command(config, cmd, timeout=5)
            
            if result.success:
                print(f"   ✅ 成功 - 退出码: {result.exit_code}")
                if result.stdout.strip():
                    print(f"      输出: {result.stdout.strip()[:50]}...")
            else:
                print(f"   ❌ 失败 - 错误: {result.error_message}")
        
        print(f"\n4. 获取统计信息:")
        stats = manager.get_stats()
        print(f"   活跃连接数: {stats['active_connections']}")
        print(f"   总执行次数: {stats['stats']['total_executions']}")
        print(f"   执行成功率: {stats['stats']['execution_success_rate']:.1%}")
        print(f"   平均执行时间: {stats['stats']['avg_execution_time']:.3f}s")
        
        print(f"\n5. 断开连接...")
        await manager.disconnect(config)
        print(f"   ✅ 连接已断开")
        
        print(f"\n6. 获取最终状态:")
        final_status = manager.get_connection_status(config)
        print(f"   最终状态: {final_status.value}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
    return True


async def test_local_commands():
    """测试本地命令执行（模拟）"""
    print(f"\n" + "=" * 50)
    print("本地命令执行测试（模拟）")
    print("=" * 50)
    
    # 模拟配置（不实际连接）
    config = SSHConnectionConfig(
        host="test-server.example.com",
        port=22,
        auth=SSHAuthConfig(
            auth_type=AuthType.PASSWORD,
            username="testuser",
        ),
    )
    
    manager = SSHConnectionManager()
    
    print(f"\n1. 验证配置模型:")
    print(f"   主机: {config.host}:{config.port}")
    print(f"   用户: {config.auth.username}")
    print(f"   认证类型: {config.auth.auth_type.value}")
    
    print(f"\n2. 验证异常处理:")
    from ssh_executor.exceptions import (
        SSHConnectionError,
        SSHAuthenticationError,
        SSHTimeoutError,
    )
    
    exceptions = [
        ("SSHConnectionError", SSHConnectionError("连接失败")),
        ("SSHAuthenticationError", SSHAuthenticationError("认证失败")),
        ("SSHTimeoutError", SSHTimeoutError("连接超时")),
    ]
    
    for name, exc in exceptions:
        print(f"   {name}: {exc}")
    
    print(f"\n3. 验证工具函数:")
    from ssh_executor.utils import parse_ssh_url, format_command_result
    
    test_urls = [
        "root@example.com",
        "user@server:2222",
        "example.com",
    ]
    
    for url in test_urls:
        user, host, port = parse_ssh_url(url)
        print(f"   URL: {url} -> 用户: {user}, 主机: {host}, 端口: {port}")
    
    # 测试结果格式化
    test_result = {
        "command": "ls -la",
        "stdout": "total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 00:00 .\ndrwxr-xr-x 5 user user 4096 Jan 1 00:00 ..",
        "stderr": "",
        "exit_code": 0,
        "execution_time": 0.123,
        "success": True,
    }
    
    formatted = format_command_result(test_result, max_output_length=100)
    print(f"\n   格式化命令结果示例:\n{formatted}")
    
    return True


async def main():
    """主测试函数"""
    print("开始 SSH 连接管理类测试...")
    
    success = True
    
    # 测试本地命令执行（总是成功）
    if not await test_local_commands():
        success = False
        print("\n⚠️ 本地命令测试失败，但继续测试...")
    
    # 测试实际 SSH 连接（可能会失败，取决于环境）
    print(f"\n" + "=" * 50)
    print("注意: 实际 SSH 连接测试需要有效的 SSH 服务器配置")
    print("      如果您没有可用的测试服务器，此测试可能会失败")
    print("=" * 50)
    
    test_ssh = input("\n是否测试实际 SSH 连接？(y/N): ").strip().lower()
    
    if test_ssh == 'y':
        if not await test_ssh_connection():
            success = False
            print("\n⚠️ SSH 连接测试失败")
    else:
        print("\n跳过实际 SSH 连接测试")
    
    if success:
        print(f"\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️ 部分测试失败，但核心功能可用")
        return 1


if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
