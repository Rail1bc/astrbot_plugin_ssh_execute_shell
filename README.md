# SSH Execute Shell — 设计文档

通过 SSH 在远程服务器上执行 Shell 命令，以 `@filter.llm_tool` 形式注册，供 LLM 调用。

## 定位

单服务器、单文件、无外部依赖（除 asyncssh）。不做连接池，不做多服务器管理，不做缓存。

## 架构

```
LLM 调用: ssh_execute_shell(command="ls -la")
                   │
                   ▼
SSHExecuteShellPlugin
                   │
                   ├─ initialize()
                   │   └─ asyncssh.connect → create_process('bash')  ← 持久 bash session
                   │
                   ├─ 每次工具调用
                   │   ├─ command 写入 bash stdin
                   │   ├─ 追加双标记以检测输出边界
                   │   └─ 读 START-END 区间 → 返回完整结果
                   │
                   └─ terminate()
                       ├─ 写 "exit\n" → 等待 bash 退出（5s 超时）
                       └─ close session → close connection
```

## 为什么用持久 bash session（方案 B）

| 方案 | 说明 | 问题 |
|------|------|------|
| 每次新建连接 | `connect → run → close` | 每次 200-400ms 握手开销 |
| 复用连接（方案 A） | 复用 asyncssh 连接对象，每次 `run()` | 不保持 shell 状态，`cd` 后下次路径重置 |
| **持久 bash（方案 B）** | **`create_process('bash')`，反复写 stdin 读 stdout** | **省握手 + 保持状态** |

持久 bash session 的两个收益：
1. 省去 SSH 握手（TCP + 密钥交换 ≈ 200-400ms）
2. 保持 shell 状态：`cd`、环境变量、alias 均跨调用维持

## 配置

`config.yaml`：

```yaml
host: "127.0.0.1"        # 目标服务器地址
port: 22                 # SSH 端口
username: "root"         # 登录用户名
auth_type: "key"         # 认证方式: password / key
key_path: "/path/to/key" # 密钥路径（key 模式）
# password: "xxx"        # 密码（password 模式）
timeout: 30              # 命令超时秒数
```

## 工具签名

```python
@filter.llm_tool(name="ssh_execute_shell")
async def ssh_execute_shell(self, event: AstrMessageEvent, command: str) -> str
```

- `command` — 要在远程服务器上执行的 Shell 命令
- 返回 `stdout` / `stderr` / 错误信息
- 只接受 `command` 一个参数，不使用 `background` 和 `env`
- 注意：不支持交互式命令（top/vim/htop 等）

## 输出边界检测

因 bash 不会告知命令何时执行完，采用**双标记区间提取法**：

```python
UID = uuid.hex
START = f"---CMD_START_{UID}---"
END   = f"---CMD_END_{UID}---"

# 写入 stdin
proc.stdin.write(f"echo '{START}'\n{command}\necho '{END}'\n")

# 读取 stdout，提取 START 与 END 之间的内容
output = []
while True:
    line = await proc.stdout.readline()
    if START in line:
        continue        # 跳过 START 行
    if END in line:
        break           # 到达结束标记
    output.append(line)
```

双标记用于在 bash 的非结构化输出中精确划定命令结果的起止区间。

## 无输出与纯 stderr 处理

命令执行后，调用方收到的结果根据以下规则组合：

| 场景 | 返回格式 |
|------|----------|
| stdout 非空，stderr 非空 | stdout + `\n--- stderr ---\n` + stderr |
| stdout 非空，stderr 为空 | 仅 stdout |
| stdout 为空，stderr 非空 | `⚠️ 命令执行完成，无标准输出，但有 stderr:\n` + stderr |
| stdout 为空，stderr 为空 | `✅ 命令执行成功，无输出` |

## 优雅关闭流程

`terminate()` 执行以下三步：

```
1. 往 bash stdin 写入 "exit\n"
2. 等待 bash 进程退出，设 5 秒超时
   ├─ 5 秒内正常退出 → 继续
   └─ 超时 → 强制 kill 进程
3. close session → close connection
```

这样大部分情况下 bash 能正常走完退出流程，清理掉子进程，不会留下孤儿进程。

## 错误与边界处理

| 场景 | 处理 |
|------|------|
| SSH 连接失败（主机不通/密钥错误/密码错误） | 不重试，直接向上抛出错误信息，tool 返回给 LLM 感知 |
| 连接中断（网络波动导致 TCP 断开） | 检测到连接失效时，tool 返回连接错误信息，由 LLM 感知并决定是否重试 |
| 命令超时不返回 | `asyncio.wait_for` 包裹读取循环，超时后丢弃 session 重建 |
| bash 进程意外退出 | 检测到退出时重新 `connect + create_process` |
| 大输出 | 截断至 **6000 字符**，末尾追加 `\n... (output truncated at 6000 chars)` |
| 无输出 / 纯 stderr | 参考上方"无输出与纯 stderr 处理"一节 |
| 特殊字符 / 多行命令 | 双标记区间提取法天然兼容；写入 stdin 时原始透传，不额外转义 |
| 交互式命令（top/vim/htop）| 不支持，已在工具描述中注明 |

## 依赖

- `asyncssh` — SSH 客户端

## 文件

```
astrbot_plugin_ssh_execute_shell/
├── main.py          ← 插件入口，全部逻辑在此
├── config.yaml      ← SSH 连接配置
├── metadata.yaml    ← 插件元信息
├── README.md        ← 本文档
├── requirements.txt ← 依赖清单
├── .gitignore
└── LICENSE
```
