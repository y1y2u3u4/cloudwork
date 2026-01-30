"""
CloudWork Telegram Bot - Main Entry Point

云端 Claude Code 工作空间的 Telegram Bot 主程序。
"""

import asyncio
import logging
import sys
import signal
from typing import Optional

from telegram import Update
from telegram.ext import Application

from ..utils.config import settings
from .handlers.commands import get_command_handlers
from .handlers.messages import get_message_handlers
from .handlers.callbacks import get_callback_handlers
from .services.task import task_manager
from .services.cron_notifier import init_cron_notifier, cron_notifier
from .services.memory import init_memory

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


# =====================================
# 应用生命周期
# =====================================

async def post_init(application: Application) -> None:
    """应用初始化后的回调"""
    logger.info("Bot 初始化完成")

    # 设置 Bot 命令菜单
    from telegram import BotCommand
    commands = [
        BotCommand("skills", "查看可用技能"),
        BotCommand("target", "切换执行目标 (VPS/本地)"),
        BotCommand("cron", "定时任务管理"),
        BotCommand("project", "切换项目"),
        BotCommand("clear", "清理会话上下文"),
        BotCommand("memory", "记忆系统管理"),
        BotCommand("sessions", "查看和切换会话"),
        BotCommand("new", "创建新会话"),
        BotCommand("model", "切换模型"),
        BotCommand("mode", "切换执行模式"),
        BotCommand("settings", "查看当前设置"),
        BotCommand("status", "查看运行状态"),
        BotCommand("cancel", "取消当前任务"),
        BotCommand("start", "开始使用 / 帮助信息"),
    ]

    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot 命令菜单已设置")
    except Exception as e:
        logger.warning(f"设置命令菜单失败: {e}")

    # 启动 Cron 通知服务（监听 cron 任务输出并发送通知）
    try:
        notifier = init_cron_notifier(application.bot)
        await notifier.start()
        logger.info("Cron 通知服务已启动，监听 data/cron_outputs/ 目录")
    except Exception as e:
        logger.error(f"启动 Cron 通知服务失败: {e}", exc_info=True)


async def post_shutdown(application: Application) -> None:
    """应用关闭前的回调"""
    logger.info("Bot 正在关闭...")

    # 停止 Cron 通知服务
    if cron_notifier:
        await cron_notifier.stop()

    # 清理所有运行中的任务
    await task_manager.cleanup_all_tasks()

    logger.info("Bot 已关闭")


async def error_handler(update: object, context) -> None:
    """全局错误处理"""
    logger.error(f"Exception while handling an update: {context.error}")

    # 记录更详细的错误信息
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    logger.error(f"Traceback:\n{tb_string}")

    # 尝试通知用户
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ 发生内部错误，请稍后重试"
            )
        except Exception:
            pass


# =====================================
# 主函数
# =====================================

def main():
    """主函数"""
    logger.info("Starting CloudWork Bot...")
    logger.info(f"Python version: {sys.version}")

    # 验证配置
    errors = settings.validate_config()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)

    # 显示配置信息
    allowed_users = settings.telegram_allowed_users
    if allowed_users:
        logger.info(f"Allowed users: {allowed_users}")
    else:
        logger.warning("No allowed users configured - development mode (all users allowed)")

    logger.info(f"Default model: {settings.default_model}")
    logger.info(f"Default mode: {settings.default_mode}")
    logger.info(f"Work directory: {settings.work_dir}")
    logger.info(f"Workspace directory: {settings.workspace_dir}")

    # 初始化记忆系统
    init_memory(settings.data_dir)
    logger.info(f"Memory system initialized: {settings.data_dir}/memory")

    # 创建应用（启用并发更新处理，允许在任务执行时响应其他命令）
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)  # 启用并发更新处理
        .build()
    )

    # 注册错误处理器
    application.add_error_handler(error_handler)

    # 注册命令处理器
    for handler in get_command_handlers():
        application.add_handler(handler)
    logger.info("Command handlers registered")

    # 注册消息处理器
    for handler in get_message_handlers():
        application.add_handler(handler)
    logger.info("Message handlers registered")

    # 注册回调处理器
    for handler in get_callback_handlers():
        application.add_handler(handler)
    logger.info("Callback handlers registered")

    # 启动 Bot
    logger.info("Bot is starting polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # 丢弃积压的消息
    )


def run_async():
    """异步运行入口（用于某些部署环境）"""
    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
