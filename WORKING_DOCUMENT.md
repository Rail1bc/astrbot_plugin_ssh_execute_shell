# SSH Execute Shell 插件工作文档

## 📋 文档信息
- **创建日期**: 2025-03-12
- **最后更新**: 2025-03-12
- **版本**: v1.0.0
- **状态**: 需求分析与设计阶段

## 🎯 项目背景与问题定义

### 1. 问题陈述
当前 AstrBot 在执行远程服务器操作时存在显著性能问题：
- **高延迟**: 每个 SSH 命令执行都有 200-500ms 的额外开销
- **低效连接**: 每次执行都需要重新建立 SSH 连接
- **体验割裂**: 开发者需要在本地和远程操作之间切换思维模式

### 2. 实测数据（基于实际测试）
```python
# 测试结果对比
本地执行: 3.19ms (3个系统命令)
SSH远程执行: 627.51ms (相同3个命令)
性能差异: 196.6倍
```

### 3. SSH 开销分解
1. **TCP 连接建立**: 50-150ms
2. **SSH 协议协商**: 100-200ms
3. **身份验证**: 50-100ms
4. **命令传输与返回**: 20-50ms
5. **网络往返延迟**: 取决于距离

## 🚀 项目愿景

**让远程服务器操作达到接近本地操作的体验**

### 核心目标
- **透明化**: 开发者无需关心操作是在本地还是远程
- **高性能**: 大幅降低远程操作的延迟
- **易用性**: 提供简单直观的 API 接口
- **可靠性**: 完善的错误处理和重试机制

## 📋 功能需求

### 1. 基础功能 (MVP)
- [ ] **F1.1**: 基本的 SSH 远程命令执行
- [ ] **F1.2**: 支持用户名/密码认证
- [ ] **F1.3**: 支持 SSH 密钥认证
- [ ] **F1.4**: 简单的错误处理
- [ ] **F1.5**: 超时控制

### 2. 性能优化功能
- [ ] **F2.1**: SSH 连接池管理
- [ ] **F2.2**: 连接复用机制
- [ ] **F2.3**: 批量命令执行
- [ ] **F2.4**: 异步执行支持
- [ ] **F2.5**: 结果缓存机制

### 3. 高级功能
- [ ] **F3.1**: 透明化 API (类似 astrbot_execute_shell)
- [ ] **F3.2**: 多服务器管理
- [ ] **F3.3**: 负载均衡
- [ ] **F3.4**: 健康检查
- [ ] **F3.5**: 监控和统计

### 4. 企业级功能
- [ ] **F4.1**: 审计日志
- [ ] **F4.2**: 访问控制
- [ ] **F4.3**: 密钥轮换
- [ ] **F4.4**: 高可用支持

## 🏗️ 架构设计

### 1. 核心组件设计

#### 1.1 ConnectionManager (连接管理器)
```python
class ConnectionManager:
    """管理 SSH 连接池"""
    
    def __init__(self):
        self.pools = {}  # host -> ConnectionPool
        self.config = {}  # 连接配置
    
    async def get_connection(self, host, user):
        """获取或创建连接"""
    
    async def release_connection(self, connection):
        """释放连接回池"""
    
    def health_check(self):
        """连接健康检查"""
```

#### 1.2 CommandExecutor (命令执行器)
```python
class CommandExecutor:
    """执行远程命令"""
    
    def __init__(self, connection_manager):
        self.cm = connection_manager
        self.cache = ResultCache()
    
    async def execute(self, host, command, **kwargs):
        """执行单个命令"""
    
    async def batch_execute(self, host, commands, **kwargs):
        """批量执行命令"""
    
    async def stream_execute(self, host, command, callback):
        """流式执行（实时输出）"""
```

#### 1.3 ResultCache (结果缓存)
```python
class ResultCache:
    """缓存常用命令结果"""
    
    def __init__(self, ttl=60):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        """获取缓存结果"""
    
    def set(self, key, value):
        """设置缓存"""
    
    def invalidate(self, pattern):
        """使缓存失效"""
```

### 2. API 设计目标

#### 目标 API 使用方式
```python
# 理想的使用方式
result = await ssh_execute_shell(
    host="root@117.72.179.121",
    command="ls -la /var/log",
    timeout=30,
    background=False
)

# 批量执行
results = await ssh_batch_execute(
    host="root@server",
    commands=[
        "apt update",
        "apt upgrade -y",
        "systemctl restart nginx"
    ]
)

# 透明化调用（最终目标）
# 开发者无需知道操作的是本地还是远程
result = await execute_shell("ls -la", host="remote")
```

### 3. 配置设计
```yaml
ssh_connections:
  server1:
    host: "192.168.1.100"
    port: 22
    user: "root"
    auth_type: "key"  # password/key
    key_path: "/path/to/private_key"
    
  server2:
    host: "example.com"
    port: 2222
    user: "admin"
    auth_type: "password"
    password: "${ENV_SSH_PASSWORD}"

connection_pool:
  max_size: 10
  max_idle: 300  # 秒
  health_check_interval: 60

cache:
  enabled: true
  ttl: 60  # 秒
  max_size: 1000
```

## 📊 性能指标与目标

### 1. 延迟目标
| 场景 | 传统 SSH | 本插件目标 | 提升 |
|------|----------|------------|------|
| 首次连接+命令 | 400-700ms | 400-700ms | 0% |
| 复用连接命令 | 300-600ms | 50-100ms | 80-85% |
| 批量命令(5个) | 1500-3000ms | 400-800ms | 70-75% |
| 缓存命中命令 | 300-600ms | 1-5ms | 99% |

### 2. 资源使用目标
- **内存使用**: < 50MB (100个连接)
- **CPU使用**: < 5% (正常负载)
- **连接数**: 支持 100+ 并发连接

### 3. 可靠性目标
- **可用性**: 99.9%
- **错误恢复**: < 1秒
- **数据一致性**: 100%

## 🔧 技术实现细节

### 1. 连接复用机制
```python
# 使用 SSH ControlMaster 实现连接复用
ssh_config = """
Host *
  ControlMaster auto
  ControlPath ~/.ssh/control-%r@%h:%p
  ControlPersist 10m
"""
```

### 2. 批量执行优化
```python
# 将多个命令合并为一个脚本传输
commands = ["cmd1", "cmd2", "cmd3"]
script = "#!/bin/bash\n" + "\n".join(commands)
# 一次性传输并执行脚本
```

### 3. 智能缓存策略
```python
# 基于命令指纹的缓存
def get_command_fingerprint(command, env_vars, working_dir):
    """生成命令的唯一指纹"""
    data = f"{command}|{sorted(env_vars.items())}|{working_dir}"
    return hashlib.md5(data.encode()).hexdigest()
```

### 4. 异步执行架构
```python
async def execute_with_timeout(connection, command, timeout):
    """带超时的异步执行"""
    try:
        return await asyncio.wait_for(
            connection.execute(command),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        # 优雅处理超时
        raise SSHTimeoutError(f"Command timeout after {timeout}s")
```

## 🧪 测试策略

### 1. 单元测试
- 连接管理测试
- 命令执行测试
- 缓存逻辑测试
- 错误处理测试

### 2. 集成测试
- 实际 SSH 服务器连接测试
- 性能基准测试
- 并发压力测试
- 故障恢复测试

### 3. 性能测试
```python
# 性能测试脚本
async def performance_test():
    # 测试各种场景的性能
    scenarios = [
        ("单命令", ["ls -la"]),
        ("批量命令", ["cmd1", "cmd2", "cmd3"]),
        ("大输出命令", ["cat /var/log/syslog"]),
    ]
    
    for name, commands in scenarios:
        start = time.time()
        await executor.batch_execute("test-server", commands)
        elapsed = time.time() - start
        print(f"{name}: {elapsed:.3f}s")
```

## 📅 开发计划

### Phase 1: 基础实现 (2周)
- 第1周: SSH 基础连接与命令执行
- 第2周: 错误处理与基本配置

### Phase 2: 性能优化 (3周)
- 第3周: 连接池实现
- 第4周: 批量执行优化
- 第5周: 缓存机制

### Phase 3: 高级特性 (3周)
- 第6周: 透明化 API
- 第7周: 异步支持
- 第8周: 监控和统计

### Phase 4: 稳定与优化 (2周)
- 第9周: 测试与调试
- 第10周: 文档与发布

## 🚨 风险与缓解

### 1. 技术风险
- **SSH 协议复杂性**: 使用成熟的 SSH 库 (paramiko/asyncssh)
- **并发控制**: 使用 asyncio 和连接池管理
- **内存泄漏**: 严格的资源管理和测试

### 2. 安全风险
- **密钥泄露**: 安全的密钥存储机制
- **未授权访问**: 严格的访问控制
- **审计缺失**: 完整的操作日志

### 3. 运维风险
- **连接泄漏**: 自动化的连接回收
- **性能下降**: 实时监控和告警
- **配置错误**: 配置验证和文档

## 📈 成功指标

### 1. 技术指标
- 延迟降低 80% 以上
- 支持 100+ 并发连接
- 99.9% 的可用性

### 2. 用户体验指标
- API 使用满意度 > 4.5/5
- 学习曲线 < 1小时
- 故障恢复时间 < 1分钟

### 3. 业务指标
- 服务器管理效率提升 50%
- 运维成本降低 30%
- 开发者采用率 > 80%

## 📚 参考资料

1. **SSH 协议规范**: RFC 4250-4256
2. **Paramiko 文档**: https://www.paramiko.org/
3. **AsyncSSH 文档**: https://asyncssh.readthedocs.io/
4. **AstrBot 插件开发指南**: https://docs.astrbot.app/
5. **性能优化模式**: 《高性能网站建设指南》

## 🤝 团队与贡献

### 核心团队
- **产品负责人**: 迫害
- **技术负责人**: 寒露
- **架构师**: Rail1bc

### 贡献指南
1. Fork 项目仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request
5. 通过代码审查

---

**文档版本历史**
- v1.0.0 (2025-03-12): 初始版本，包含完整的需求分析和设计

**下一步行动**
1. 审查并确认需求文档
2. 开始 Phase 1 的开发
3. 搭建开发环境
4. 创建第一个原型
