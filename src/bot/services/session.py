"""
CloudWork Session Management Service

管理用户会话：创建、切换、归档、持久化
"""

import json
import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from ...utils.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """会话数据结构"""
    id: str
    name: str
    created_at: str
    last_active: str
    message_count: int = 0
    archived: bool = False
    project: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        return cls(**data)


@dataclass
class UserData:
    """用户数据结构"""
    active: Optional[str] = None  # 当前活跃会话 ID
    sessions: Dict[str, dict] = field(default_factory=dict)
    model: str = "sonnet"
    execution_mode: str = "auto"
    project: str = "default"
    pending_name: Optional[str] = None  # 预设的会话名称
    # 执行目标: "vps" (本机执行) 或 "local" (代理到本地节点)
    execution_target: str = "vps"
    # 本地节点配置 (Tailscale IP + 端口)
    local_node_url: Optional[str] = None
    # 本地节点 API Token (可选，用于远程认证)
    local_node_token: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "sessions": self.sessions,
            "model": self.model,
            "execution_mode": self.execution_mode,
            "project": self.project,
            "execution_target": self.execution_target,
            "local_node_url": self.local_node_url,
            "local_node_token": self.local_node_token,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserData':
        return cls(
            active=data.get("active"),
            sessions=data.get("sessions", {}),
            model=data.get("model", "sonnet"),
            execution_mode=data.get("execution_mode", "auto"),
            project=data.get("project", "default"),
            execution_target=data.get("execution_target", "vps"),
            local_node_url=data.get("local_node_url"),
            local_node_token=data.get("local_node_token"),
        )


class SessionManager:
    """会话管理器"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or settings.data_dir
        self.sessions_file = os.path.join(self.data_dir, "sessions.json")
        self.user_sessions: Dict[int, UserData] = {}
        self.message_to_session: Dict[int, str] = {}  # message_id -> session_id 映射
        self._ensure_data_dir()
        self.load_sessions()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)

    def load_sessions(self):
        """从文件加载会话数据"""
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for user_id_str, user_data in data.items():
                    user_id = int(user_id_str)
                    self.user_sessions[user_id] = UserData.from_dict(user_data)

                logger.info(f"已加载 {len(self.user_sessions)} 个用户的会话数据")
            except Exception as e:
                logger.error(f"加载会话数据失败: {e}")
                self.user_sessions = {}
        else:
            logger.info("会话数据文件不存在，使用空数据")

    def save_sessions(self):
        """保存会话数据到文件"""
        try:
            data = {
                str(user_id): user_data.to_dict()
                for user_id, user_data in self.user_sessions.items()
            }

            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug("会话数据已保存")
        except Exception as e:
            logger.error(f"保存会话数据失败: {e}")

    def get_or_create_user_data(self, user_id: int) -> UserData:
        """获取或创建用户数据"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = UserData()
            self.save_sessions()
        return self.user_sessions[user_id]

    def get_active_session_id(self, user_id: int) -> Optional[str]:
        """获取用户当前活跃会话 ID"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.active

    def set_active_session(self, user_id: int, session_id: str):
        """设置用户当前活跃会话"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.active = session_id

        # 更新会话最后活跃时间
        if session_id in user_data.sessions:
            user_data.sessions[session_id]["last_active"] = datetime.now().isoformat()

        self.save_sessions()

    def create_session(
        self,
        user_id: int,
        session_id: str,
        name: Optional[str] = None,
        project: Optional[str] = None
    ) -> Session:
        """创建新会话"""
        user_data = self.get_or_create_user_data(user_id)
        now = datetime.now().isoformat()

        # 使用预设名称或生成名称
        if not name:
            name = user_data.pending_name or f"会话 {len(user_data.sessions) + 1}"
            user_data.pending_name = None

        session = Session(
            id=session_id,
            name=name,
            created_at=now,
            last_active=now,
            message_count=1,
            project=project or user_data.project
        )

        user_data.sessions[session_id] = session.to_dict()
        user_data.active = session_id
        self.save_sessions()

        logger.info(f"创建新会话: {session_id[:8]}... 名称: {name}")
        return session

    def update_session(
        self,
        user_id: int,
        session_id: str,
        name: Optional[str] = None,
        increment_count: bool = True
    ):
        """更新会话信息"""
        user_data = self.get_or_create_user_data(user_id)

        if session_id in user_data.sessions:
            session = user_data.sessions[session_id]
            session["last_active"] = datetime.now().isoformat()

            if name:
                session["name"] = name

            if increment_count:
                session["message_count"] = session.get("message_count", 0) + 1

            self.save_sessions()

    def touch_session(self, user_id: int, session_id: str):
        """
        触碰会话，更新最后活跃时间和消息计数

        这是 update_session 的简化版本，用于普通消息处理
        """
        self.update_session(user_id, session_id, name=None, increment_count=True)

    def update_session_id(self, user_id: int, old_session_id: str, new_session_id: str):
        """
        更新会话 ID（当 Claude 返回真正的 session ID 时使用）

        Args:
            user_id: 用户 ID
            old_session_id: 旧的会话 ID（通常是 pending_ 开头的临时 ID）
            new_session_id: 新的会话 ID（Claude 返回的 UUID 格式）
        """
        user_data = self.get_or_create_user_data(user_id)

        if old_session_id in user_data.sessions:
            # 获取旧会话数据
            session_data = user_data.sessions[old_session_id]

            # 用新 ID 保存会话数据
            user_data.sessions[new_session_id] = session_data

            # 删除旧 ID 的数据
            del user_data.sessions[old_session_id]

            # 更新活跃会话 ID
            if user_data.active == old_session_id:
                user_data.active = new_session_id

            self.save_sessions()
            logger.info(f"更新会话 ID: {old_session_id[:8]}... -> {new_session_id[:8]}...")

    def get_session(self, user_id: int, session_id: str) -> Optional[dict]:
        """获取会话信息"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.sessions.get(session_id)

    def get_all_sessions(self, user_id: int, include_archived: bool = False) -> List[dict]:
        """获取用户所有会话"""
        user_data = self.get_or_create_user_data(user_id)
        sessions = []

        for session_id, session_data in user_data.sessions.items():
            if not include_archived and session_data.get("archived", False):
                continue
            sessions.append({
                "id": session_id,
                **session_data
            })

        # 按最后活跃时间排序
        sessions.sort(key=lambda x: x.get("last_active", ""), reverse=True)
        return sessions

    def get_archived_sessions(self, user_id: int) -> List[dict]:
        """获取已归档的会话"""
        user_data = self.get_or_create_user_data(user_id)
        sessions = []

        for session_id, session_data in user_data.sessions.items():
            if session_data.get("archived", False):
                sessions.append({
                    "id": session_id,
                    **session_data
                })

        sessions.sort(key=lambda x: x.get("last_active", ""), reverse=True)
        return sessions

    def archive_session(self, user_id: int, session_id: str):
        """归档会话"""
        user_data = self.get_or_create_user_data(user_id)

        if session_id in user_data.sessions:
            user_data.sessions[session_id]["archived"] = True

            # 如果归档的是当前活跃会话，清除活跃状态
            if user_data.active == session_id:
                user_data.active = None

            self.save_sessions()
            logger.info(f"归档会话: {session_id[:8]}...")

    def unarchive_session(self, user_id: int, session_id: str):
        """恢复归档的会话"""
        user_data = self.get_or_create_user_data(user_id)

        if session_id in user_data.sessions:
            user_data.sessions[session_id]["archived"] = False
            user_data.active = session_id
            self.save_sessions()
            logger.info(f"恢复会话: {session_id[:8]}...")

    def delete_session(self, user_id: int, session_id: str) -> bool:
        """删除会话"""
        user_data = self.get_or_create_user_data(user_id)

        if session_id in user_data.sessions:
            del user_data.sessions[session_id]

            if user_data.active == session_id:
                user_data.active = None

            self.save_sessions()
            logger.info(f"删除会话: {session_id[:8]}...")
            return True

        return False

    def clear_session_context(self, user_id: int, session_id: str) -> Optional[str]:
        """
        清理会话上下文（保留会话名称，删除旧会话并创建新会话）

        Args:
            user_id: 用户 ID
            session_id: 要清理的会话 ID

        Returns:
            新会话 ID，如果失败则返回 None
        """
        user_data = self.get_or_create_user_data(user_id)

        if session_id not in user_data.sessions:
            return None

        # 保存旧会话信息
        old_session = user_data.sessions[session_id]
        old_name = old_session.get("name", "未命名")
        old_project = old_session.get("project")

        # 删除旧会话
        del user_data.sessions[session_id]

        # 生成新会话 ID
        new_session_id = self.generate_pending_session_id(user_id)

        # 创建同名新会话
        now = datetime.now().isoformat()
        new_session = Session(
            id=new_session_id,
            name=old_name,
            created_at=now,
            last_active=now,
            message_count=0,
            project=old_project
        )

        user_data.sessions[new_session_id] = new_session.to_dict()
        user_data.active = new_session_id

        self.save_sessions()
        logger.info(f"清理会话上下文: {session_id[:8]}... -> {new_session_id[:8]}...")

        return new_session_id

    def check_and_archive_sessions(self, auto_archive_minutes: Optional[int] = None):
        """
        检查并自动归档长时间未活动的会话

        Args:
            auto_archive_minutes: 自动归档时间（分钟），默认使用配置值
        """
        if auto_archive_minutes is None:
            auto_archive_minutes = settings.auto_archive_minutes

        now = datetime.now()
        archived_count = 0

        for user_id, user_data in self.user_sessions.items():
            for session_id, session_data in list(user_data.sessions.items()):
                if session_data.get("archived", False):
                    continue

                last_active_str = session_data.get("last_active", "")
                if not last_active_str:
                    continue

                try:
                    last_active = datetime.fromisoformat(last_active_str)
                    inactive_minutes = (now - last_active).total_seconds() / 60

                    if inactive_minutes > auto_archive_minutes:
                        session_data["archived"] = True

                        if user_data.active == session_id:
                            user_data.active = None

                        archived_count += 1
                        logger.info(
                            f"自动归档会话: {session_id[:8]}... "
                            f"(用户 {user_id}, 不活跃 {inactive_minutes:.0f} 分钟)"
                        )
                except Exception as e:
                    logger.warning(f"解析会话时间出错: {e}")

        if archived_count > 0:
            self.save_sessions()
            logger.info(f"自动归档了 {archived_count} 个会话")

    # =====================================
    # 用户设置管理
    # =====================================

    def get_user_model(self, user_id: int) -> str:
        """获取用户选择的模型"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.model

    def set_user_model(self, user_id: int, model: str):
        """设置用户模型"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.model = model
        self.save_sessions()

    def get_user_execution_mode(self, user_id: int) -> str:
        """获取用户执行模式"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.execution_mode

    def set_user_execution_mode(self, user_id: int, mode: str):
        """设置用户执行模式"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.execution_mode = mode
        self.save_sessions()

    def get_user_project(self, user_id: int) -> str:
        """获取用户当前项目"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.project

    def set_user_project(self, user_id: int, project: str):
        """设置用户项目（同时清除活跃会话，为新项目创建新会话）"""
        user_data = self.get_or_create_user_data(user_id)
        old_project = user_data.project
        user_data.project = project

        # 切换项目时清除活跃会话，这样可以在新项目中启动新任务
        # 即使旧项目有运行中的任务，也不会阻塞新项目的操作
        if old_project != project:
            user_data.active = None
            logger.info(f"切换项目 {old_project} -> {project}，清除活跃会话")

        self.save_sessions()

    def set_pending_name(self, user_id: int, name: str):
        """设置待创建会话的名称"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.pending_name = name

    # =====================================
    # 执行目标管理 (VPS / Local)
    # =====================================

    def get_execution_target(self, user_id: int) -> str:
        """获取用户执行目标 ('vps' 或 'local')"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.execution_target

    def set_execution_target(self, user_id: int, target: str):
        """设置用户执行目标"""
        if target not in ("vps", "local"):
            raise ValueError(f"无效的执行目标: {target}")
        user_data = self.get_or_create_user_data(user_id)
        user_data.execution_target = target
        self.save_sessions()
        logger.info(f"用户 {user_id} 切换执行目标: {target}")

    def get_local_node_url(self, user_id: int) -> Optional[str]:
        """获取用户的本地节点 URL"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.local_node_url

    def set_local_node_url(self, user_id: int, url: Optional[str]):
        """设置用户的本地节点 URL (例如 http://100.x.x.x:2026)"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.local_node_url = url
        self.save_sessions()
        logger.info(f"用户 {user_id} 设置本地节点: {url}")

    def get_local_node_token(self, user_id: int) -> Optional[str]:
        """获取用户的本地节点 API Token"""
        user_data = self.get_or_create_user_data(user_id)
        return user_data.local_node_token

    def set_local_node_token(self, user_id: int, token: Optional[str]):
        """设置用户的本地节点 API Token"""
        user_data = self.get_or_create_user_data(user_id)
        user_data.local_node_token = token
        self.save_sessions()
        logger.info(f"用户 {user_id} 设置本地节点 Token: {'***' if token else 'None'}")

    # =====================================
    # 消息-会话映射
    # =====================================

    def map_message_to_session(self, message_id: int, session_id: str):
        """记录消息与会话的映射"""
        self.message_to_session[message_id] = session_id

    def get_session_from_message(self, message_id: int) -> Optional[str]:
        """根据消息 ID 获取会话 ID"""
        return self.message_to_session.get(message_id)

    # =====================================
    # 工具函数
    # =====================================

    @staticmethod
    def generate_pending_session_id(user_id: int) -> str:
        """
        生成临时会话 ID（用于新对话开始时，Claude 还未返回真正的 session_id）
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:8]
        return f"pending_{user_id}_{hash_part}"

    @staticmethod
    def is_pending_session(session_id: Optional[str]) -> bool:
        """检查是否是临时会话 ID"""
        return session_id is not None and session_id.startswith("pending_")


# 全局会话管理器实例
session_manager = SessionManager()
