#!/usr/bin/env python3
"""
测试SSH命令执行器功能
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ssh_executor.core.executor import SSHCommandExecutor


async def test_local_command():
    """测试本地命令执行（使用localhost）"""
    print("=== 测试本地命令执行 ===")
    
    executor = SSHCommandExecutor(default_timeout=10)
    
    try:
        # 测试简单的命令
        print("1. 测试简单命令: echo 'Hello SSH'")
        result = await executor.execute(
            host="localhost",
            username="root",
            command="echo 'Hello SSH'"
        )
        print(f"   结果: exit_code={result.exit_code}")
        print(f"   输出: {result.stdout}")
        print(f"   成功: {result.success}")
        
        # 测试带工作目录的命令
        print("\n2. 测试带工作目录的命令: pwd")
        result = await executor.execute(
            host="localhost",
            username="root",
            command="pwd",
            workdir="/tmp"
        )
        print(f"   结果: exit_code={result.exit_code}")
        print(f"   输出: {result.stdout}")
        
        # 测试错误命令
        print("\n3. 测试错误命令: command_not_found")
        result = await executor.execute(
            host="localhost",
            username="root",
            command="command_not_found"
        )
        print(f"   结果: exit_code={result.exit_code}")
        print(f"   错误输出: {result.stderr}")
        print(f"   成功: {result.success}")
        
        # 测试统计信息
        print("\n4. 测试统计信息:")
        stats = executor.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
    finally:
        await executor.close()


async def test_batch_commands():
    """测试批量命令执行"""
    print("\n=== 测试批量命令执行 ===")
    
    executor = SSHCommandExecutor(default_timeout=10)
    
    try:
        commands = [
            "echo 'Command 1'",
            "echo 'Command 2'",
            "echo 'Command 3'",
            "false",  # 这个命令会失败
            "echo 'Command 5'"
        ]
        
        print(f"执行 {len(commands)} 个命令 (stop_on_error=True):")
        results = await executor.execute_multi(
            host="localhost",
            username="root",
            commands=commands,
            stop_on_error=True
        )
        
        print(f"实际执行了 {len(results)} 个命令 (遇到错误停止)")
        for i, result in enumerate(results):
            status = "✅" if result.success else "❌"
            print(f"  {status} 命令 {i+1}: exit_code={result.exit_code}")
        
        print(f"\n执行 {len(commands)} 个命令 (stop_on_error=False):")
        results = await executor.execute_multi(
            host="localhost",
            username="root",
            commands=commands,
            stop_on_error=False
        )
        
        print(f"实际执行了 {len(results)} 个命令 (继续执行)")
        for i, result in enumerate(results):
            status = "✅" if result.success else "❌"
            print(f"  {status} 命令 {i+1}: exit_code={result.exit_code}")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
    finally:
        await executor.close()


async def test_async_context():
    """测试异步上下文管理器"""
    print("\n=== 测试异步上下文管理器 ===")
    
    async with SSHCommandExecutor(default_timeout=10) as executor:
        print("在异步上下文中执行命令...")
        result = await executor.execute(
            host="localhost",
            username="root",
            command="echo 'Async Context Test'"
        )
        print(f"   结果: {result.stdout}")
        
        stats = executor.get_stats()
        print(f"   统计: 执行了 {stats['total_commands']} 个命令")
    
    print("上下文管理器已自动关闭")


async def main():
    """主测试函数"""
    print("SSH命令执行器功能测试")
    print("=" * 50)
    
    await test_local_command()
    await test_batch_commands()
    await test_async_context()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
