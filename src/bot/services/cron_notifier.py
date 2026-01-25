"""
Cron 任务通知服务

监听 data/cron_outputs/ 目录，处理 cron 任务输出并发送 Telegram 通知。
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# 中国时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))

from telegram import Bot
from telegram.constants import ParseMode

from ...utils.config import settings

logger = logging.getLogger(__name__)


class CronNotifier:
    """Cron 任务通知服务"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.outputs_dir = Path(settings.work_dir) / "data" / "cron_outputs"
        self.processed_dir = Path(settings.work_dir) / "data" / "cron_processed"
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # 确保目录存在
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """启动通知服务"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"Cron 通知服务已启动，监听目录: {self.outputs_dir}")

    async def stop(self):
        """停止通知服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cron 通知服务已停止")

    async def _watch_loop(self):
        """监听循环"""
        from .cron_config import cron_config

        while self._running:
            try:
                # 检查通知是否启用
                if cron_config.is_notification_enabled():
                    await self._process_pending_outputs()
                else:
                    logger.debug("通知已禁用，跳过处理")
            except Exception as e:
                logger.error(f"处理 cron 输出失败: {e}", exc_info=True)

            # 从配置读取检查间隔
            interval_minutes = cron_config.get_notification_interval()
            await asyncio.sleep(interval_minutes * 60)

    async def _process_pending_outputs(self):
        """处理待发送的输出文件"""
        # 获取所有 JSON 文件
        files = sorted(self.outputs_dir.glob("*.json"))

        for file_path in files:
            try:
                await self._process_file(file_path)
            except Exception as e:
                logger.error(f"处理文件 {file_path} 失败: {e}")
                # 移动到 processed 目录，标记为失败
                self._move_to_processed(file_path, success=False)

    async def _process_file(self, file_path: Path):
        """处理单个输出文件"""
        logger.info(f"处理 cron 输出: {file_path.name}")

        # 读取 JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 验证格式
        if not self._validate_output(data):
            logger.warning(f"无效的输出格式: {file_path.name}")
            self._move_to_processed(file_path, success=False)
            return

        # 格式化消息
        message = self._format_message(data)

        # 发送通知
        await self._send_notification(message)

        # 移动到已处理目录
        self._move_to_processed(file_path, success=True)

    def _validate_output(self, data: Dict[str, Any]) -> bool:
        """验证输出格式"""
        required_fields = ['task', 'status', 'title', 'message']
        return all(field in data for field in required_fields)

    def _format_message(self, data: Dict[str, Any]) -> str:
        """格式化通知消息"""
        status = data.get('status', 'unknown')
        title = data.get('title', '未知任务')
        message = data.get('message', '')
        task = data.get('task', 'unknown')
        created_at = data.get('created_at', '')

        # 状态图标
        if status == 'success':
            icon = '✅'
        elif status == 'error':
            icon = '❌'
        else:
            icon = 'ℹ️'

        # 格式化时间（转换为中国时区）
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                dt_china = dt.astimezone(CHINA_TZ)
                time_str = dt_china.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                time_str = created_at
        else:
            time_str = datetime.now(CHINA_TZ).strftime('%Y-%m-%d %H:%M:%S')

        return f"""{icon} **{title}**

{message}

---
🏷️ 任务: `{task}`
⏰ 时间: {time_str}"""

    async def _send_notification(self, message: str):
        """发送通知到授权用户"""
        allowed_users = settings.telegram_allowed_users
        if not allowed_users:
            logger.warning("没有配置授权用户，跳过通知")
            return

        for user_id in allowed_users:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"已发送 cron 通知到用户 {user_id}")
            except Exception as e:
                logger.error(f"发送通知到用户 {user_id} 失败: {e}")

    def _move_to_processed(self, file_path: Path, success: bool):
        """移动文件到已处理目录"""
        suffix = "_ok" if success else "_failed"
        dest = self.processed_dir / f"{file_path.stem}{suffix}{file_path.suffix}"
        shutil.move(str(file_path), str(dest))
        logger.info(f"已移动到: {dest.name}")


# 全局实例
cron_notifier: Optional[CronNotifier] = None


def init_cron_notifier(bot: Bot) -> CronNotifier:
    """初始化 cron 通知服务"""
    global cron_notifier
    cron_notifier = CronNotifier(bot)
    return cron_notifier
