"""
SSH 执行器工具函数
"""
import re
import hashlib
import socket
from typing import Optional, Tuple, Dict, Any


def format_command_result(result: Dict[str, Any], max_output_length: int = 500) -> str:
    """
    格式化命令执行结果
    
    Args:
        result: 命令执行结果字典
        max_output_length: 最大输出长度
        
    Returns:
        str: 格式化后的字符串
    """
    lines = []
    lines.append(f"命令: {result.get('command', '未知命令')}")
    
    if 'execution_time' in result:
        lines.append(f"执行时间: {result['execution_time']:.3f}s")
    
    if 'exit_code' in result:
        lines.append(f"退出码: {result['exit_code']}")
    
    if 'success' in result:
        status = "✅ 成功" if result['success'] else "❌ 失败"
        lines.append(f"状态: {status}")
    
    if 'stdout' in result and result['stdout']:
        output = result['stdout']
        if len(output) > max_output_length:
            output = output[:max_output_length] + "..."
        lines.append(f"输出:\n{output}")
    
    if 'stderr' in result and result['stderr']:
        error = result['stderr']
        if len(error) > max_output_length:
            error = error[:max_output_length] + "..."
        lines.append(f"错误:\n{error}")
    
    if 'error_message' in result and result['error_message']:
        lines.append(f"错误信息: {result['error_message']}")
    
    return "\n".join(lines)


def parse_ssh_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    解析 SSH URL
    
    Args:
        url: SSH URL，格式如 user@host:port 或 user@host
        
    Returns:
        Tuple[username, hostname, port]
    """
    # 匹配 user@host:port 或 user@host
    pattern = r'^(?:([^@]+)@)?([^:]+)(?::(\d+))?$'
    match = re.match(pattern, url)
    
    if not match:
        return None, None, None
    
    username = match.group(1) or "root"
    hostname = match.group(2)
    port_str = match.group(3)
    
    port = 22  # 默认端口
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            port = 22
    
    return username, hostname, port


def validate_hostname(hostname: str) -> bool:
    """
    验证主机名是否有效
    
    Args:
        hostname: 主机名
        
    Returns:
        bool: 是否有效
    """
    if not hostname or len(hostname) > 255:
        return False
    
    # 允许的字符
    allowed = re.compile(r'^[a-zA-Z0-9.-]+$')
    if not allowed.match(hostname):
        return False
    
    # 检查每个标签
    labels = hostname.split('.')
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith('-') or label.endswith('-'):
            return False
    
    return True


def safe_parse_int(value: Any, default: int = 0) -> int:
    """
    安全地解析整数
    
    Args:
        value: 要解析的值
        default: 默认值
        
    Returns:
        int: 解析后的整数
    """
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_command_fingerprint(
    command: str,
    env_vars: Optional[Dict[str, str]] = None,
    working_dir: Optional[str] = None,
    host: Optional[str] = None
) -> str:
    """
    获取命令的唯一指纹
    
    Args:
        command: 命令字符串
        env_vars: 环境变量
        working_dir: 工作目录
        host: 主机名
        
    Returns:
        str: 命令指纹（MD5哈希）
    """
    data_parts = []
    
    # 添加命令
    data_parts.append(f"command:{command}")
    
    # 添加环境变量（按字母顺序排序）
    if env_vars:
        sorted_vars = sorted(env_vars.items())
        data_parts.append(f"env:{sorted_vars}")
    
    # 添加工作目录
    if working_dir:
        data_parts.append(f"cwd:{working_dir}")
    
    # 添加主机名
    if host:
        data_parts.append(f"host:{host}")
    
    # 计算 MD5 哈希
    data_str = "|".join(data_parts)
    return hashlib.md5(data_str.encode()).hexdigest()


def calculate_timeout(
    base_timeout: float,
    multiplier: float = 1.0,
    min_timeout: float = 1.0,
    max_timeout: float = 300.0
) -> float:
    """
    计算超时时间
    
    Args:
        base_timeout: 基础超时时间
        multiplier: 超时倍数
        min_timeout: 最小超时时间
        max_timeout: 最大超时时间
        
    Returns:
        float: 计算后的超时时间
    """
    timeout = base_timeout * multiplier
    timeout = max(timeout, min_timeout)
    timeout = min(timeout, max_timeout)
    return timeout


def is_valid_port(port: int) -> bool:
    """
    检查端口号是否有效
    
    Args:
        port: 端口号
        
    Returns:
        bool: 是否有效
    """
    return 1 <= port <= 65535


def get_local_ip() -> str:
    """
    获取本地 IP 地址
    
    Returns:
        str: 本地 IP 地址
    """
    try:
        # 创建一个临时 socket 来获取本地 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
