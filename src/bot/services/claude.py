"""
CloudWork Claude CLI Execution Service

执行 Claude Code CLI 命令，处理流式输出，支持交互式问答
"""

import os
import re
import asyncio
import json
import logging
import time
from typing import Optional, Tuple, Dict, Any, Callable, Awaitable

from ...utils.config import settings
from .task import TaskState, RunningTask, task_manager
from .session import session_manager

logger = logging.getLogger(__name__)

# 常量
COMMAND_TIMEOUT = 300  # 命令超时时间（秒）
MESSAGE_UPDATE_INTERVAL = 1.5  # 消息更新间隔（秒）
MAX_ACCUMULATED_TEXT = 50000  # 最大累积文本长度
USER_INPUT_TIMEOUT = 120  # 用户输入超时时间（秒）

# 可用模型
AVAILABLE_MODELS = {
    "sonnet": "Claude Sonnet - 平衡",
    "opus": "Claude Opus - 最强",
    "haiku": "Claude Haiku - 最快"
}

# 执行模式
EXECUTION_MODES = {
    "auto": "自动模式 - 跳过确认",
    "plan": "计划模式 - 先生成计划"
}


class ClaudeExecutor:
    """Claude CLI 执行器"""

    def __init__(self):
        self.work_dir = settings.work_dir
        self.workspace_dir = settings.workspace_dir
        self.projects: Dict[str, str] = {}
        self._discover_projects()

    def _discover_projects(self):
        """发现 workspace 目录中的项目"""
        # default 项目使用 work_dir 作为实际路径
        self.projects = {"default": self.work_dir}

        if not os.path.exists(self.workspace_dir):
            return

        try:
            for item in os.listdir(self.workspace_dir):
                # 跳过隐藏文件和 .gitkeep
                if item.startswith('.'):
                    continue

                item_path = os.path.join(self.workspace_dir, item)
                if os.path.isdir(item_path):
                    # 所有目录都识别为项目（不再要求 CLAUDE.md）
                    self.projects[item] = item_path

                    # 同时检查子目录
                    for sub_item in os.listdir(item_path):
                        if sub_item.startswith('.'):
                            continue
                        sub_path = os.path.join(item_path, sub_item)
                        if os.path.isdir(sub_path):
                            project_name = f"{item}/{sub_item}"
                            self.projects[project_name] = sub_path

            logger.info(f"发现 {len(self.projects)} 个项目: {list(self.projects.keys())}")
        except Exception as e:
            logger.error(f"发现项目时出错: {e}")

    def get_project_dir(self, project: str) -> str:
        """获取项目目录"""
        if project in self.projects:
            return self.projects[project]
        return self.work_dir

    def get_user_project_dir(self, user_id: int) -> str:
        """获取用户当前项目目录"""
        project = session_manager.get_user_project(user_id)
        return self.get_project_dir(project)

    def build_claude_env(self) -> dict:
        """构建 Claude CLI 环境变量"""
        return settings.get_claude_env()

    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """检查是否是有效的 UUID 格式"""
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))

    def build_command(
        self,
        prompt: str,
        session_id: Optional[str],
        model: str,
        execution_mode: str
    ) -> list:
        """构建 Claude CLI 命令"""
        # 检查是否是有效的 session ID（必须是 UUID 格式，且不是 pending_ 开头）
        is_valid_session = (
            session_id and
            not session_id.startswith("pending_") and
            self.is_valid_uuid(session_id)
        )

        if is_valid_session:
            cmd = [
                'unbuffer',
                'claude', '--resume', session_id,
                '-p', prompt,
                '--model', model,
                '--output-format', 'stream-json',
                '--verbose'
            ]
        else:
            cmd = [
                'unbuffer',
                'claude',
                '-p', prompt,
                '--model', model,
                '--output-format', 'stream-json',
                '--verbose'
            ]

        # 根据执行模式添加权限标志
        if execution_mode == "plan":
            cmd.extend(['--permission-mode', 'plan'])
        else:
            cmd.append('--dangerously-skip-permissions')

        return cmd

    async def execute_stream(
        self,
        prompt: str,
        session_id: Optional[str],
        user_id: int,
        chat_id: int,
        message_id: int,
        progress_callback: Callable[[str, Optional[str]], Awaitable[None]],
        question_callback: Optional[Callable[[Dict[str, Any], RunningTask], Awaitable[None]]] = None,
        model: Optional[str] = None,
        execution_mode: Optional[str] = None,
        work_dir: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        异步流式执行 Claude Code 命令

        Args:
            prompt: 用户输入
            session_id: 会话 ID
            user_id: 用户 ID
            chat_id: 聊天 ID
            message_id: 状态消息 ID
            progress_callback: 进度更新回调 (text, status)
            question_callback: 问题回调 (用于 AskUserQuestion)
            model: 模型名称
            execution_mode: 执行模式
            work_dir: 工作目录

        Returns:
            (output, new_session_id)
        """
        # 获取用户设置
        if not model:
            model = session_manager.get_user_model(user_id)
        if not execution_mode:
            execution_mode = session_manager.get_user_execution_mode(user_id)
        if not work_dir:
            work_dir = self.get_user_project_dir(user_id)

        # 构建命令
        cmd = self.build_command(prompt, session_id, model, execution_mode)
        logger.info(f"流式执行命令 (model={model}): {' '.join(cmd[:5])}...")

        # 创建子进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env=self.build_claude_env()
        )

        # 创建任务
        task = task_manager.create_task(
            process=process,
            session_id=session_id,
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id
        )

        task_key = (user_id, session_id)
        new_session_id = session_id

        try:
            # 处理流式输出
            new_session_id = await self._process_stream(
                task, progress_callback, question_callback
            )

            task.state = TaskState.COMPLETED

            # 检查是否需要重试（会话不存在的情况）
            if task.session_not_found and session_id:
                logger.info(f"会话 {session_id} 不存在，自动创建新会话重试...")
                task_manager.remove_task(user_id, session_id)

                # 删除无效的旧会话，防止元数据被错误继承到新会话
                session_manager.delete_session(user_id, session_id)

                await progress_callback("🔄 会话已失效，正在创建新会话...", None)

                # 递归调用，不使用 session_id
                return await self.execute_stream(
                    prompt=prompt,
                    session_id=None,
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    progress_callback=progress_callback,
                    question_callback=question_callback,
                    model=model,
                    execution_mode=execution_mode,
                    work_dir=work_dir
                )

        except asyncio.TimeoutError:
            logger.warning(f"任务超时: user={user_id}")
            task.state = TaskState.CANCELLED
            process.terminate()
            await process.wait()
            task.accumulated_text += "\n\n⚠️ 任务执行超时"

        except asyncio.CancelledError:
            logger.info(f"任务被取消: user={user_id}")
            task.state = TaskState.CANCELLED
            process.terminate()
            await process.wait()
            task.accumulated_text += "\n\n⚠️ 任务已取消"

        except Exception as e:
            logger.error(f"流式执行错误: {e}")
            task.state = TaskState.CANCELLED
            if process.returncode is None:
                process.terminate()
                await process.wait()
            task.accumulated_text += f"\n\n❌ 执行错误: {str(e)}"

        finally:
            task_manager.remove_task(user_id, session_id)

        return task.accumulated_text, new_session_id or session_id

    async def _process_stream(
        self,
        task: RunningTask,
        progress_callback: Callable[[str, Optional[str]], Awaitable[None]],
        question_callback: Optional[Callable[[Dict[str, Any], RunningTask], Awaitable[None]]]
    ) -> Optional[str]:
        """处理流式输出"""
        new_session_id = task.session_id
        process = task.process
        line_count = 0

        try:
            while True:
                if task.state == TaskState.CANCELLED:
                    logger.info("任务已取消，停止处理")
                    break

                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=COMMAND_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.warning("readline() 超时")
                    break

                if not line_bytes:
                    break

                line_text = line_bytes.decode('utf-8', errors='replace').strip()
                if not line_text:
                    continue

                line_count += 1

                # 解析 JSON
                if line_text.startswith('{'):
                    try:
                        event = json.loads(line_text)
                        result = await self._handle_stream_event(
                            event, task, progress_callback, question_callback
                        )
                        if result:
                            new_session_id = result
                    except json.JSONDecodeError:
                        task.accumulated_text += line_text + "\n"
                else:
                    task.accumulated_text += line_text + "\n"

                # 限制累积文本大小
                if len(task.accumulated_text) > MAX_ACCUMULATED_TEXT:
                    task.accumulated_text = task.accumulated_text[-MAX_ACCUMULATED_TEXT:]

            await process.wait()
            logger.info(f"流式输出完成，共处理 {line_count} 行")

        except asyncio.TimeoutError:
            logger.warning("流处理超时")
            raise
        except Exception as e:
            logger.error(f"流处理异常: {e}")
            raise

        return new_session_id

    async def _handle_stream_event(
        self,
        event: Dict[str, Any],
        task: RunningTask,
        progress_callback: Callable[[str, Optional[str]], Awaitable[None]],
        question_callback: Optional[Callable[[Dict[str, Any], RunningTask], Awaitable[None]]]
    ) -> Optional[str]:
        """处理流式事件"""
        event_type = event.get("type", "")
        new_session_id = None

        # 处理 system 事件
        if event_type == "system":
            new_session_id = event.get("session_id")
            if new_session_id:
                task.session_id = new_session_id
                logger.info(f"获取到 session_id: {new_session_id[:8]}...")

            tools = event.get("tools", [])
            if tools:
                await progress_callback(
                    task.accumulated_text,
                    f"⚙️ 初始化完成，加载了 {len(tools)} 个工具..."
                )

        # 处理 assistant 事件
        elif event_type == "assistant":
            message = event.get("message", {})
            content = message.get("content", [])

            for block in content:
                block_type = block.get("type", "")

                if block_type == "text":
                    text = block.get("text", "")
                    if text:
                        if task.accumulated_text and not task.accumulated_text.endswith('\n'):
                            task.accumulated_text += "\n"
                        task.accumulated_text += text
                        await progress_callback(task.accumulated_text, None)

                elif block_type == "tool_use":
                    tool_name = block.get("name", "unknown")
                    task.current_tool = tool_name
                    task.tool_call_count += 1  # 递增工具调用计数
                    logger.info(f"工具调用: {tool_name} (第 {task.tool_call_count} 次)")
                    await progress_callback(
                        task.accumulated_text,
                        f"🔧 正在使用工具: {tool_name} ({task.tool_call_count})"
                    )

                    # 处理 AskUserQuestion
                    if tool_name == "AskUserQuestion" and question_callback:
                        await question_callback(block, task)

            new_session_id = event.get("session_id") or new_session_id

        # 处理 user 事件
        elif event_type == "user":
            content = event.get("content", [])
            for block in content:
                if block.get("type") == "tool_result":
                    task.current_tool = None

        # 处理 result 事件
        elif event_type == "result":
            is_error = event.get("is_error", False)
            errors = event.get("errors", [])

            if is_error and errors:
                error_str = str(errors)
                if "No conversation found" in error_str:
                    logger.warning(f"会话不存在错误")
                    task.session_not_found = True
                    task.state = TaskState.COMPLETED
                    return new_session_id
                else:
                    logger.error(f"Claude 返回错误: {error_str[:200]}")
                    task.accumulated_text = f"❌ 执行错误: {error_str}"
                    task.state = TaskState.COMPLETED
                    return new_session_id

            result_text = event.get("result", "")
            # 只有在没有累积文本时才使用 result_text（避免覆盖中间输出）
            if result_text and not task.accumulated_text.strip():
                task.accumulated_text = result_text
            new_session_id = event.get("session_id") or new_session_id
            task.state = TaskState.COMPLETED

        # 定期更新进度
        current_time = time.time()
        if current_time - task.last_update_time >= MESSAGE_UPDATE_INTERVAL:
            status = f"🔧 正在执行: {task.current_tool} ({task.tool_call_count})" if task.current_tool else None
            await progress_callback(task.accumulated_text, status)
            task.last_update_time = current_time

        return new_session_id

    def execute_sync(
        self,
        prompt: str,
        session_id: Optional[str],
        user_id: int,
        model: Optional[str] = None,
        work_dir: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        同步执行 Claude Code 命令（用于简单的 /run 命令）

        Returns:
            (output, new_session_id)
        """
        import subprocess

        if not model:
            model = session_manager.get_user_model(user_id)
        if not work_dir:
            work_dir = self.get_user_project_dir(user_id)

        # 构建命令
        if session_id:
            cmd = ['claude', '--resume', session_id, '-p', prompt]
        else:
            cmd = ['claude', '-p', prompt, '--output-format', 'json']
        cmd.append('--dangerously-skip-permissions')
        cmd.extend(['--model', model])

        logger.info(f"同步执行命令: {' '.join(cmd[:5])}...")

        try:
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                env=self.build_claude_env()
            )

            output = result.stdout if result.stdout else result.stderr
            new_session_id = session_id

            # 解析 JSON 获取 session_id
            if not session_id and output:
                try:
                    lines = output.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                json_output = json.loads(line)
                                new_session_id = json_output.get("session_id")
                                if "result" in json_output:
                                    output = json_output.get("result", output)
                                break
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning(f"解析 JSON 输出时出错: {e}")

            return output, new_session_id

        except subprocess.TimeoutExpired:
            return f"⚠️ 任务超时（{COMMAND_TIMEOUT}秒）", session_id
        except Exception as e:
            return f"❌ 执行错误: {str(e)}", session_id


# 全局执行器实例
claude_executor = ClaudeExecutor()
