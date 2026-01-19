"""
CloudWork User Authentication

用户认证和授权管理
"""

import logging
from typing import Set

from .config import settings

logger = logging.getLogger(__name__)

# 授权用户缓存
_authorized_users: Set[int] = set()


def _load_authorized_users():
    """加载授权用户列表"""
    global _authorized_users

    allowed_users = settings.telegram_allowed_users
    if not allowed_users:
        logger.warning("未配置授权用户列表 (TELEGRAM_ALLOWED_USERS)")
        return

    # allowed_users 已经是 List[int]，由 pydantic 处理
    _authorized_users = set(allowed_users)
    logger.info(f"已加载 {len(_authorized_users)} 个授权用户")


def is_authorized(user_id: int) -> bool:
    """
    检查用户是否授权

    Args:
        user_id: Telegram 用户 ID

    Returns:
        是否授权
    """
    # 懒加载
    if not _authorized_users:
        _load_authorized_users()

    # 如果没有配置授权列表，允许所有用户（开发模式）
    if not _authorized_users:
        logger.warning(f"未配置授权列表，允许用户 {user_id} 访问")
        return True

    return user_id in _authorized_users


def get_authorized_users() -> Set[int]:
    """获取所有授权用户"""
    if not _authorized_users:
        _load_authorized_users()
    return _authorized_users.copy()


def add_authorized_user(user_id: int):
    """添加授权用户（运行时）"""
    _authorized_users.add(user_id)
    logger.info(f"添加授权用户: {user_id}")


def remove_authorized_user(user_id: int):
    """移除授权用户（运行时）"""
    _authorized_users.discard(user_id)
    logger.info(f"移除授权用户: {user_id}")
