"""
CloudWork Command Handlers

处理 Telegram Bot 的各类命令
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...utils.config import settings
from ...utils.auth import is_authorized
from ...utils.formatters import escape_markdown, safe_truncate
from ..services.session import session_manager
from ..services.claude import claude_executor, AVAILABLE_MODELS, EXECUTION_MODES

logger = logging.getLogger(__name__)


# =====================================
# 帮助类命令
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    welcome_text = f"""
👋 *欢迎使用 CloudWork!*

你好 {user.first_name}！这是一个云端 Claude Code 工作空间。

*快速开始:*
• 直接发送消息开始对话
• /new \\[名称\\] 创建新会话
• /sessions 查看和切换会话

*更多命令:*
• /help 查看完整帮助
• /model 切换模型
• /mode 切换执行模式
• /project 切换项目
• /settings 查看当前设置

当前模型: *{session_manager.get_user_model(user.id)}*
执行模式: *{session_manager.get_user_execution_mode(user.id)}*
"""

    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    help_text = """
📖 *CloudWork 使用指南*

*会话管理:*
• 直接发消息 \\- 在当前会话中对话
• /new \\[名称\\] \\- 创建新会话
• /sessions \\- 查看和切换会话
• /archived \\- 查看归档会话
• 回复历史消息 \\- 自动切换到该会话

*执行命令:*
• /run <prompt> \\- 独立执行（不影响会话）

*设置:*
• /model \\- 切换模型 \\(sonnet/opus/haiku\\)
• /mode \\- 切换执行模式 \\(auto/plan\\)
• /project \\- 切换工作项目

*系统:*
• /status \\- 系统状态
• /settings \\- 当前设置
• /cancel \\- 取消当前任务

*执行模式说明:*
• auto: 自动模式，跳过确认直接执行
• plan: 计划模式，先生成执行计划

*提示:*
• 会话 30 分钟无活动自动归档
• 可以通过回复历史消息快速切换会话
"""

    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


# =====================================
# 会话管理命令
# =====================================

async def list_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示会话列表"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    sessions = session_manager.get_all_sessions(user.id, include_archived=False)
    active_session_id = session_manager.get_active_session_id(user.id)

    if not sessions:
        await update.message.reply_text(
            "📭 暂无会话\n\n发送消息开始新对话，或使用 /new 创建会话"
        )
        return

    # 构建会话列表按钮
    keyboard = []
    for session in sessions[:10]:  # 最多显示10个
        session_id = session.get("id", "")
        name = session.get("name", "未命名")
        message_count = session.get("message_count", 0)

        # 标记当前活跃会话
        prefix = "▶️ " if session_id == active_session_id else ""
        button_text = f"{prefix}{name} ({message_count}条)"

        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"switch_session:{session_id}"
            )
        ])

    # 添加功能按钮
    keyboard.append([
        InlineKeyboardButton("➕ 新建会话", callback_data="new_session"),
        InlineKeyboardButton("📦 归档会话", callback_data="show_archived")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 *会话列表*\n\n点击切换会话:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """创建新会话"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    # 获取会话名称（如果提供）
    args = context.args
    name = " ".join(args) if args else None

    if name:
        # 预设名称，等待第一条消息时创建
        session_manager.set_pending_name(user.id, name)
        await update.message.reply_text(
            f"✅ 已准备新会话: *{escape_markdown(name)}*\n\n发送消息开始对话",
            parse_mode='Markdown'
        )
    else:
        # 清除当前会话，下次消息自动创建
        user_data = session_manager.get_or_create_user_data(user.id)
        user_data.active = None
        session_manager.save_sessions()

        await update.message.reply_text(
            "✅ 已准备新会话\n\n发送消息开始对话，会话将自动命名"
        )


async def archived_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示归档会话"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    sessions = session_manager.get_archived_sessions(user.id)

    if not sessions:
        await update.message.reply_text("📭 暂无归档会话")
        return

    # 构建归档会话按钮
    keyboard = []
    for session in sessions[:10]:
        session_id = session.get("id", "")
        name = session.get("name", "未命名")
        message_count = session.get("message_count", 0)

        button_text = f"📦 {name} ({message_count}条)"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"unarchive_session:{session_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("◀️ 返回活跃会话", callback_data="show_sessions")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📦 *归档会话*\n\n点击恢复会话:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def delete_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除会话"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "用法: /delete <会话ID前8位>\n\n使用 /sessions 查看会话列表"
        )
        return

    session_id_prefix = args[0]

    # 查找匹配的会话
    user_data = session_manager.get_or_create_user_data(user.id)
    matching_session = None

    for session_id in user_data.sessions.keys():
        if session_id.startswith(session_id_prefix):
            matching_session = session_id
            break

    if not matching_session:
        await update.message.reply_text(f"❌ 未找到匹配的会话: {session_id_prefix}")
        return

    session_name = user_data.sessions[matching_session].get("name", "未命名")

    if session_manager.delete_session(user.id, matching_session):
        await update.message.reply_text(f"✅ 已删除会话: {session_name}")
    else:
        await update.message.reply_text("❌ 删除会话失败")


# =====================================
# 设置命令
# =====================================

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换或查看当前模型"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    current_model = session_manager.get_user_model(user.id)

    if args:
        # 直接切换模型
        new_model = args[0].lower()
        if new_model in AVAILABLE_MODELS:
            session_manager.set_user_model(user.id, new_model)
            await update.message.reply_text(
                f"✅ 已切换到 *{new_model}*\n\n{AVAILABLE_MODELS[new_model]}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ 无效模型: {new_model}\n\n可用: sonnet, opus, haiku"
            )
        return

    # 显示模型选择按钮
    keyboard = []
    for model_key, model_desc in AVAILABLE_MODELS.items():
        prefix = "✅ " if model_key == current_model else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{model_key} - {model_desc}",
                callback_data=f"set_model:{model_key}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🤖 *模型选择*\n\n当前模型: *{current_model}*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换或查看执行模式"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    current_mode = session_manager.get_user_execution_mode(user.id)

    if args:
        # 直接切换模式
        new_mode = args[0].lower()
        if new_mode in EXECUTION_MODES:
            session_manager.set_user_execution_mode(user.id, new_mode)
            await update.message.reply_text(
                f"✅ 已切换到 *{new_mode}* 模式\n\n{EXECUTION_MODES[new_mode]}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ 无效模式: {new_mode}\n\n可用: auto, plan"
            )
        return

    # 显示模式选择按钮
    keyboard = []
    for mode_key, mode_desc in EXECUTION_MODES.items():
        prefix = "✅ " if mode_key == current_mode else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{mode_key} - {mode_desc}",
                callback_data=f"set_mode:{mode_key}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⚙️ *执行模式*\n\n当前模式: *{current_mode}*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换或查看当前项目"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    current_project = session_manager.get_user_project(user.id)

    if args:
        # 直接切换项目
        new_project = args[0]
        if new_project in claude_executor.projects:
            session_manager.set_user_project(user.id, new_project)
            project_path = claude_executor.projects[new_project]
            await update.message.reply_text(
                f"✅ 已切换到项目: *{new_project}*\n\n路径: `{project_path}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ 无效项目: {new_project}\n\n使用 /project 查看可用项目"
            )
        return

    # 显示项目选择按钮
    keyboard = []
    for project_key, project_path in claude_executor.projects.items():
        prefix = "✅ " if project_key == current_project else ""
        # 截断过长的路径
        display_path = project_path if len(project_path) < 30 else "..." + project_path[-27:]
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{project_key}",
                callback_data=f"set_project:{project_key}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    current_path = claude_executor.projects.get(current_project, "未知")

    await update.message.reply_text(
        f"📁 *项目选择*\n\n当前项目: *{current_project}*\n路径: `{current_path}`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示当前设置"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    model = session_manager.get_user_model(user.id)
    mode = session_manager.get_user_execution_mode(user.id)
    project = session_manager.get_user_project(user.id)
    active_session = session_manager.get_active_session_id(user.id)

    # 获取活跃会话名称
    session_name = "无"
    if active_session:
        session_data = session_manager.get_session(user.id, active_session)
        if session_data:
            session_name = session_data.get("name", active_session[:8])

    project_path = claude_executor.get_project_dir(project)

    settings_text = f"""
⚙️ *当前设置*

*模型*: {model} \\({AVAILABLE_MODELS.get(model, '')}\\)
*模式*: {mode} \\({EXECUTION_MODES.get(mode, '')}\\)
*项目*: {project}
*路径*: `{project_path}`
*会话*: {session_name}

*快捷修改:*
• /model <名称> \\- 切换模型
• /mode <模式> \\- 切换执行模式
• /project <项目> \\- 切换项目
"""

    await update.message.reply_text(
        settings_text,
        parse_mode='Markdown'
    )


# =====================================
# 执行命令
# =====================================

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """独立执行命令（不影响会话）"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "用法: /run <prompt>\n\n此命令独立执行，不影响当前会话"
        )
        return

    prompt = " ".join(args)

    # 发送执行中状态
    status_message = await update.message.reply_text("⏳ 执行中...")

    try:
        # 同步执行
        output, _ = claude_executor.execute_sync(
            prompt=prompt,
            session_id=None,
            user_id=user.id
        )

        # 格式化输出
        output = safe_truncate(output, 3500)

        await status_message.edit_text(
            f"✅ *执行完成*\n\n{output}",
            parse_mode=None  # 使用纯文本避免解析问题
        )

    except Exception as e:
        logger.error(f"执行失败: {e}")
        await status_message.edit_text(f"❌ 执行失败: {str(e)}")


# =====================================
# 系统命令
# =====================================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示系统状态"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    import platform
    import os

    # 获取系统信息
    hostname = platform.node()
    python_version = platform.python_version()

    # 获取项目数量
    project_count = len(claude_executor.projects)

    # 获取用户会话数量
    sessions = session_manager.get_all_sessions(user.id, include_archived=True)
    active_count = len([s for s in sessions if not s.get("archived", False)])
    archived_count = len([s for s in sessions if s.get("archived", False)])

    status_text = f"""
📊 *系统状态*

*服务器*: {hostname}
*Python*: {python_version}
*项目数*: {project_count}

*你的会话*:
• 活跃: {active_count}
• 归档: {archived_count}

*工作目录*: `{settings.work_dir}`
"""

    await update.message.reply_text(
        status_text,
        parse_mode='Markdown'
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消当前任务"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    from ..services.task import task_manager

    # 获取用户所有任务
    tasks = task_manager.get_user_tasks(user.id)

    if not tasks:
        await update.message.reply_text("ℹ️ 没有正在运行的任务")
        return

    # 取消所有任务
    cancelled_count = 0
    for task in tasks:
        await task_manager.cancel_task(user.id, task.session_id)
        cancelled_count += 1

    await update.message.reply_text(f"✅ 已取消 {cancelled_count} 个任务")


# =====================================
# 命令注册辅助函数
# =====================================

def get_command_handlers():
    """返回所有命令处理器，用于注册到 Application"""
    from telegram.ext import CommandHandler

    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("sessions", list_sessions),
        CommandHandler("new", new_session),
        CommandHandler("archived", archived_sessions),
        CommandHandler("delete", delete_session),
        CommandHandler("model", model_command),
        CommandHandler("mode", mode_command),
        CommandHandler("project", project_command),
        CommandHandler("settings", settings_command),
        CommandHandler("run", run_command),
        CommandHandler("status", status_command),
        CommandHandler("cancel", cancel_command),
    ]
