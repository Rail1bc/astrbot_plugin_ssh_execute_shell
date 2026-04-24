# 🔐 SSH 远程命令执行器

<div align="center">

[![AstrBot](https://img.shields.io/badge/AstrBot-4.0%2B-blue)](https://github.com/Soulter/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.1.0-orange)](https://github.com/Rail1bc/astrbot_plugin_ssh_execute_shell)

**让 LLM 通过 SSH 在远程服务器上执行 Shell 命令**

</div>

---

## 📖 简介

本插件允许你的 AstrBot 通过 SSH 连接到远程服务器，执行 Shell 命令。你只需要在聊天中说出你想做的事情，LLM 就会自动调用 SSH 工具完成操作。

> ⚠️ **安全提示**：本插件的所有命令操作**仅限管理员**执行，普通成员无法使用。

### 典型场景

- 🖥️ **远程运维**：直接在群里说"帮我看看服务器负载"，Bot 自动 SSH 连接执行 `top` / `htop`
- 📂 **文件管理**：查看目录结构、检查日志文件、清理磁盘空间
- 🚀 **服务管理**：重启服务、查看进程状态、检查端口监听
- 📊 **快速诊断**：网络连通性测试、磁盘使用率查看、系统信息查询

---

## ✨ 功能特性

- **🔗 持久 SSH 会话**：复用同一个 bash 进程，`cd`、环境变量、alias 跨命令保持
- **⚡ 低延迟**：避免每次命令都重新握手，省去 200-400ms 的连接开销
- **📦 大输出自动截断**：超过 6000 字符自动截断，避免刷屏
- **🔒 管理员保护**：非管理员调用会被拒绝，并提示联系管理员授权
- **🔄 自动重连**：网络中断或超时后自动重建连接

---

## 🚀 安装

### 方法一：插件市场安装（推荐）

1. 打开 AstrBot WebUI
2. 进入「插件管理」页面
3. 在插件市场中搜索「SSH 命令执行器」
4. 点击安装，等待完成

### 方法二：手动安装

```bash
# 克隆仓库到插件目录
cd /AstrBot/data/plugins
git clone https://github.com/Rail1bc/astrbot_plugin_ssh_execute_shell.git

# 重启 AstrBot 或重载插件
```

---

## ⚙️ 配置

在 AstrBot WebUI → 插件管理 → SSH 命令执行器 中进行配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `host` | 目标服务器地址 | `127.0.0.1` |
| `port` | SSH 端口 | `22` |
| `username` | 登录用户名 | `root` |
| `auth_type` | 认证方式 (`key` / `password`) | `key` |
| `key_path` | 密钥文件路径（key 模式） | `""` |
| `password` | 登录密码（password 模式） | `""` |
| `timeout` | 命令超时秒数 | `30` |
| `known_hosts` | known_hosts 文件路径，留空跳过校验 | `""` |

> 💡 **首次使用**：推荐将 `known_hosts` 留空，避免首次连接时的 host key 校验问题。后续可设置为 `/root/.ssh/known_hosts` 进行严格校验。

---

## 🛠️ 使用方式

配置完成后，LLM 会自动根据对话上下文调用 SSH 工具。你只需要像平常一样聊天即可。

**示例对话：**

> 🧑 用户：帮我看看服务器现在负载怎么样
> 🤖 Bot：好的，我来查一下
> ```
> 10:28:25 up 3 days, 14:22,  0 users,  load average: 0.08, 0.03, 0.01
> ```
> 当前负载很低，CPU 很空闲~

---

## 📋 注意事项

- ❌ 不支持交互式命令（如 `top`、`vim`、`htop` 等）
- 🔒 仅管理员可执行命令
- 📏 输出超过 6000 字符会自动截断
- 🔄 连接断开时会自动重连

---

## 📄 许可证

本项目基于 MIT 许可证开源。
