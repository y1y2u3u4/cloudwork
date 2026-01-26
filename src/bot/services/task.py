"""
CloudWork Task Management Service

管理运行中的任务：状态跟踪、取消、超时处理
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    """任务状态枚举"""
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class RunningTask:
    """运行中的任务"""
    process: Any  # asyncio.subprocess.Process
    session_id: Optional[str]
    chat_id: int
    message_id: int
    user_id: int
    state: str = TaskState.RUNNING
    accumulated_text: str = ""
    current_tool: Optional[str] = None
    current_tool_display: Optional[str] = None  # 格式化后的工具调用显示
    tool_call_count: int = 0  # 工具调用计数器，用于区分连续相同工具调用
    pending_question: Optional[str] = None
    last_update_time: float = field(default_factory=time.time)
    input_event: Any = None  # asyncio.Event
    user_reply: Optional[str] = None
    session_not_found: bool = False
    question_options: Optional[List[Dict[str, str]]] = None

    def __post_init__(self):
        if self.input_event is None:
            self.input_event = asyncio.Event()


@dataclass
class PendingPlan:
    """待执行的计划"""
    prompt: str
    plan_text: str
    message_id: int
    created_at: float
    session_id: str
    user_data: dict


class TaskManager:
    """任务管理器"""

    # 任务超时时间（秒）
    DEFAULT_TIMEOUT = 300

    # 用户输入超时时间（秒）
    USER_INPUT_TIMEOUT = 120

    # 计划超时时间（秒）
    PLAN_TIMEOUT = 300

    def __init__(self):
        # 运行中的任务 (user_id, session_id) -> RunningTask
        self.running_tasks: Dict[Tuple[int, Optional[str]], RunningTask] = {}

        # 待执行的计划 (user_id, session_id) -> PendingPlan
        self.pending_plans: Dict[Tuple[int, str], PendingPlan] = {}

    # =====================================
    # 任务管理
    # =====================================

    def create_task(
        self,
        process: Any,
        session_id: Optional[str],
        chat_id: int,
        message_id: int,
        user_id: int
    ) -> RunningTask:
        """创建新任务"""
        task = RunningTask(
            process=process,
            session_id=session_id,
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
            input_event=asyncio.Event()
        )

        task_key = (user_id, session_id)
        self.running_tasks[task_key] = task

        logger.info(f"创建任务: user={user_id}, session={session_id[:8] if session_id else 'new'}...")
        return task

    def get_task(self, user_id: int, session_id: Optional[str]) -> Optional[RunningTask]:
        """获取任务"""
        task_key = (user_id, session_id)
        return self.running_tasks.get(task_key)

    def get_user_tasks(self, user_id: int) -> List[RunningTask]:
        """获取用户所有任务"""
        return [
            task for (uid, _), task in self.running_tasks.items()
            if uid == user_id
        ]

    def remove_task(self, user_id: int, session_id: Optional[str]):
        """移除任务"""
        task_key = (user_id, session_id)
        if task_key in self.running_tasks:
            del self.running_tasks[task_key]
            logger.info(f"移除任务: user={user_id}, session={session_id[:8] if session_id else 'unknown'}...")

    async def cancel_task(self, user_id: int, session_id: Optional[str]) -> bool:
        """取消任务"""
        task = self.get_task(user_id, session_id)
        if not task:
            return False

        task.state = TaskState.CANCELLED

        # 终止进程
        if task.process and task.process.returncode is None:
            try:
                task.process.terminate()
                await asyncio.wait_for(task.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                task.process.kill()
                await task.process.wait()
            except Exception as e:
                logger.error(f"终止进程失败: {e}")

        # 触发输入事件（如果在等待输入）
        if task.input_event:
            task.input_event.set()

        self.remove_task(user_id, session_id)
        logger.info(f"取消任务: user={user_id}, session={session_id[:8] if session_id else 'unknown'}...")
        return True

    def set_task_state(self, user_id: int, session_id: Optional[str], state: str):
        """设置任务状态"""
        task = self.get_task(user_id, session_id)
        if task:
            task.state = state

    def set_user_reply(self, user_id: int, session_id: Optional[str], reply: str):
        """设置用户回复"""
        task = self.get_task(user_id, session_id)
        if task:
            task.user_reply = reply
            if task.input_event:
                task.input_event.set()
            return True
        return False

    def has_running_task(self, user_id: int, session_id: Optional[str] = None) -> bool:
        """检查是否有运行中的任务"""
        if session_id:
            task = self.get_task(user_id, session_id)
            return task is not None and task.state == TaskState.RUNNING
        else:
            tasks = self.get_user_tasks(user_id)
            return any(t.state == TaskState.RUNNING for t in tasks)

    def is_waiting_input(self, user_id: int, session_id: Optional[str]) -> bool:
        """检查任务是否在等待用户输入"""
        task = self.get_task(user_id, session_id)
        return task is not None and task.state == TaskState.WAITING_INPUT

    # =====================================
    # 计划管理
    # =====================================

    def save_pending_plan(
        self,
        user_id: int,
        session_id: str,
        prompt: str,
        plan_text: str,
        message_id: int,
        user_data: dict
    ):
        """保存待执行的计划"""
        # 先清理过期的计划
        self._cleanup_expired_plans()

        plan = PendingPlan(
            prompt=prompt,
            plan_text=plan_text,
            message_id=message_id,
            created_at=time.time(),
            session_id=session_id,
            user_data=user_data
        )

        plan_key = (user_id, session_id)
        self.pending_plans[plan_key] = plan

        logger.info(f"保存待执行计划: user={user_id}, session={session_id[:8]}...")

    def get_pending_plan(self, user_id: int, session_id: str) -> Optional[PendingPlan]:
        """获取待执行的计划"""
        plan_key = (user_id, session_id)
        return self.pending_plans.get(plan_key)

    def remove_pending_plan(self, user_id: int, session_id: str):
        """移除待执行的计划"""
        plan_key = (user_id, session_id)
        if plan_key in self.pending_plans:
            del self.pending_plans[plan_key]
            logger.info(f"移除待执行计划: user={user_id}, session={session_id[:8]}...")

    def _cleanup_expired_plans(self):
        """清理过期的计划"""
        now = time.time()
        expired_keys = [
            key for key, plan in self.pending_plans.items()
            if now - plan.created_at > self.PLAN_TIMEOUT
        ]

        for key in expired_keys:
            del self.pending_plans[key]
            logger.info(f"清理过期计划: {key}")

    # =====================================
    # 清理
    # =====================================

    async def cleanup_all_tasks(self):
        """清理所有任务（用于关闭时）"""
        for (user_id, session_id), task in list(self.running_tasks.items()):
            try:
                await self.cancel_task(user_id, session_id)
            except Exception as e:
                logger.error(f"清理任务失败: {e}")

        self.running_tasks.clear()
        self.pending_plans.clear()
        logger.info("已清理所有任务")


# 全局任务管理器实例
task_manager = TaskManager()
