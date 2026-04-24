import asyncio
import uuid
import asyncssh
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


MAX_OUTPUT_LEN = 6000

# —— 管理员校验函数（仿照 astrbot 本体 shell 工具的 check_admin_permission 逻辑） ——
def _check_admin(event: AstrMessageEvent, operation_name: str) -> str | None:
    """检查当前用户是否为管理员。如果不是，返回错误提示；是则返回 None。"""
    if not event.is_admin():
        return (
            f"❌ 权限不足：{operation_name} 仅允许管理员使用。\n"
            f"如需授权，请管理在 AstrBot WebUI → 配置 → 基础配置 中添加您的用户ID到管理员列表。\n"
            f"您的用户ID是：{event.get_sender_id()}"
        )
    return None


@register("astrbot_plugin_ssh_execute_shell", "Rail1bc, 寒露", "通过SSH在远程服务器上执行Shell命令（仅管理员）", "1.1.0")
class SSHExecuteShellPlugin(Star):
    """通过持久 bash session 在远程服务器上执行 Shell 命令。（仅管理员可用）"""

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        # SSH 连接参数
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 22)
        self.username = self.config.get("username", "root")
        self.auth_type = self.config.get("auth_type", "key")
        self.key_path = self.config.get("key_path", "")
        self.password = self.config.get("password", "")
        self.timeout = self.config.get("timeout", 30)
        # known_hosts: 留空=跳过校验，填路径=使用该文件
        self.known_hosts = self.config.get("known_hosts", "")
        # 运行时状态
        self.conn = None          # SSH 连接
        self.proc = None          # 持久 bash 进程 (SSHClientProcess)

    async def initialize(self):
        """初始化阶段只检查配置完整性，不主动连接。连接在首次工具调用时懒建立。"""
        logger.info(
            f"SSH 插件已加载，目标服务器: {self.username}@{self.host}:{self.port}"
        )

    async def _connect(self):
        """连接远程服务器并创建持久 bash 进程。"""
        connect_kwargs = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
        }
        if self.auth_type == "key":
            connect_kwargs["client_keys"] = [self.key_path]
        else:
            connect_kwargs["password"] = self.password

        # known_hosts 处理：留空则跳过 host key 校验
        if self.known_hosts:
            connect_kwargs["known_hosts"] = self.known_hosts
        else:
            connect_kwargs["known_hosts"] = None

        self.conn = await asyncssh.connect(**connect_kwargs)
        self.proc = await self.conn.create_process("bash")
        logger.info(
            f"SSH 连接已建立: {self.username}@{self.host}:{self.port}"
        )

    async def _reconnect(self):
        """断开并重建连接。"""
        await self._cleanup_connection()
        await self._connect()
        logger.info("SSH 连接已重建")

    async def _cleanup_connection(self):
        """清理当前连接资源（不抛异常）。"""
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.write("exit\n")
                await self.proc.stdin.drain()
            if self.proc:
                try:
                    await asyncio.wait_for(self.proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.proc.kill()
        except Exception as e:
            logger.warning(f"清理 bash 进程时出现异常: {e}")
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.warning(f"关闭连接时出现异常: {e}")
        finally:
            self.proc = None
            self.conn = None

    async def _read_until_marker(self, end_marker: str) -> str:
        """从 stdout 中读取，直到遇到 end_marker 行。返回中间所有内容。"""
        lines = []
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                # 流已关闭，bash 进程可能意外退出
                raise ConnectionError("bash 进程 stdout 已关闭，连接可能已中断")
            stripped = line.rstrip("\n").rstrip("\r")
            if end_marker in stripped:
                break
            lines.append(line)
        return "".join(lines)

    @filter.llm_tool(name="ssh_execute_shell")
    async def ssh_execute_shell(self, event: AstrMessageEvent, command: str):
        """
        执行一条 shell 命令，返回 stdout/stderr。不支持交互式命令。
        仅限管理员使用。

        Args:
            command (str): 要执行的 shell 命令
        """
        # —— 管理员权限校验（仿照 astrbot 本体 shell 工具） ——
        if permission_error := _check_admin(event, "SSH 远程命令执行"):
            return permission_error

        # 检查连接是否就绪，首次访问时懒连接
        if not self.proc:
            try:
                await self._connect()
            except Exception as e:
                err_msg = f"SSH 首次连接失败: {e}"
                logger.error(err_msg)
                return err_msg
        elif self.proc.stdout.at_eof():
            # bash 进程已退出，重建连接
            try:
                await self._reconnect()
            except Exception as e:
                err_msg = f"SSH 断线重连失败: {e}"
                logger.error(err_msg)
                return err_msg

        uid = uuid.uuid4().hex
        start_marker = f"---CMD_START_{uid}---"
        end_marker = f"---CMD_END_{uid}---"

        payload = (
            f"echo '{start_marker}'\n"
            f"{command}\n"
            f"echo '{end_marker}'\n"
        )
        try:
            self.proc.stdin.write(payload)
            await self.proc.stdin.drain()
        except Exception as e:
            # 写入失败，连接可能已断开
            logger.warning(f"写入 stdin 失败，尝试重建连接: {e}")
            try:
                await self._reconnect()
            except Exception as reconnect_err:
                return f"SSH 连接已断开且重建失败: {reconnect_err}"
            # 重建成功后重试
            try:
                self.proc.stdin.write(payload)
                await self.proc.stdin.drain()
            except Exception as e2:
                return f"重建连接后写入仍然失败: {e2}"

        # 跳过 start_marker 行
        try:
            while True:
                line = await asyncio.wait_for(
                    self.proc.stdout.readline(), timeout=self.timeout
                )
                if not line:
                    raise ConnectionError("bash 进程 stdout 已关闭")
                if start_marker in line:
                    break
        except asyncio.TimeoutError:
            logger.warning("等待 START 标记超时，可能命令无输出或连接异常")
            # 尝试重建连接
            try:
                await self._reconnect()
            except Exception as e:
                pass
            return "⚠️ 命令执行超时，SSH 连接已重置"
        except ConnectionError as e:
            logger.warning(f"读取 START 标记时连接断开: {e}")
            try:
                await self._reconnect()
            except Exception:
                pass
            return f"⚠️ SSH 连接中断: {e}"

        # 读取 START 和 END 之间的输出
        stderr_lines = []
        stdout_text = ""
        try:
            stdout_text = await asyncio.wait_for(
                self._read_until_marker(end_marker), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning("等待 END 标记超时，重建连接")
            try:
                await self._reconnect()
            except Exception:
                pass
            return "⚠️ 命令执行超时，SSH 连接已重置"
        except ConnectionError as e:
            logger.warning(f"读取命令输出时连接断开: {e}")
            try:
                await self._reconnect()
            except Exception:
                pass
            return f"⚠️ SSH 连接中断: {e}"

        # 读取 stderr（非阻塞）
        try:
            while True:
                line = await asyncio.wait_for(
                    self.proc.stderr.readline(), timeout=0.5
                )
                if not line:
                    break
                stderr_lines.append(line.rstrip("\n").rstrip("\r"))
        except (asyncio.TimeoutError, Exception):
            pass  # stderr 暂时没数据或已读完，可忽略

        # 组合结果
        stderr_text = "\n".join(stderr_lines) if stderr_lines else ""
        stdout_stripped = stdout_text.rstrip("\n").rstrip("\r")

        # 输出截断
        if len(stdout_stripped) > MAX_OUTPUT_LEN:
            stdout_stripped = (
                stdout_stripped[:MAX_OUTPUT_LEN]
                + "\n... (output truncated at 6000 chars)"
            )

        if stdout_stripped and stderr_text:
            return stdout_stripped + "\n--- stderr ---\n" + stderr_text
        elif stdout_stripped:
            return stdout_stripped
        elif stderr_text:
            return f"⚠️ 命令执行完成，无标准输出，但有 stderr:\n{stderr_text}"
        else:
            return "✅ 命令执行成功，无输出"

    async def terminate(self):
        """优雅关闭：先让 bash 正常退出，再关闭 session 和连接。"""
        await self._cleanup_connection()
        logger.info("SSH 插件已关闭")
