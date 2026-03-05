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
from ..services.memory import get_memory_manager

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
• /memory 记忆系统管理
• /cron 定时任务管理
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
• /clear \\- 清理当前会话上下文
• 回复历史消息 \\- 自动切换到该会话

*引用回复:*
• 回复 Bot 消息 \\- 将 Bot 回复作为上下文引用

*执行命令:*
• /run <prompt> \\- 独立执行（不影响会话）

*设置:*
• /model \\- 切换模型 \\(sonnet/opus/haiku\\)
• /mode \\- 切换执行模式 \\(auto/plan\\)
• /project \\- 切换工作项目

*记忆系统:*
• /memory \\- 查看记忆状态
• /memory learn \\- 提取学习模式
• /memory save \\- 保存长期记忆
• /memory search \\- 搜索记忆

*定时任务:*
• /cron \\- 管理定时任务和通知

*系统:*
• /status \\- 系统状态
• /settings \\- 当前设置
• /cancel \\- 取消当前任务

*执行模式说明:*
• auto: 自动模式，跳过确认直接执行
• plan: 计划模式，先生成执行计划

*提示:*
• 会话 30 分钟无活动自动归档
• 回复 Bot 消息可将其作为上下文引用
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


async def target_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    切换执行目标 (VPS 或本地节点)

    用法:
    - /target              查看当前目标
    - /target vps          切换到 VPS 执行
    - /target local <URL>  切换到本地节点，URL 为 Desktop API 地址
    - /target local        切换到本地节点（使用已保存的 URL）
    - /target token <TOKEN> 设置本地节点 API Token
    - /target token        清除 Token
    """
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    current_target = session_manager.get_execution_target(user.id)
    current_url = session_manager.get_local_node_url(user.id)
    current_token = session_manager.get_local_node_token(user.id)

    if not args:
        # 显示当前状态和切换按钮
        status_emoji = "🖥️" if current_target == "vps" else "💻"
        url_info = f"\n本地节点: `{current_url}`" if current_url else ""
        token_info = "\nAPI Token: ✅ 已设置" if current_token else ""

        # 构建按钮
        buttons = []
        if current_target == "vps":
            # 当前是 VPS，显示切换到 Local 的按钮
            if current_url:
                buttons.append([InlineKeyboardButton("💻 切换到本地节点", callback_data="set_target:local")])
            else:
                buttons.append([InlineKeyboardButton("💻 设置本地节点", callback_data="set_target:local_setup")])
        else:
            # 当前是 Local，显示切换到 VPS 的按钮
            buttons.append([InlineKeyboardButton("🖥️ 切换到 VPS", callback_data="set_target:vps")])

        keyboard = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            f"{status_emoji} *执行目标*\n\n"
            f"当前: *{current_target.upper()}*{url_info}{token_info}\n\n"
            f"_点击按钮切换，或使用命令:_\n"
            f"`/target local <URL>` 设置本地节点\n"
            f"`/target token <TOKEN>` 设置认证",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return

    new_target = args[0].lower()

    if new_target == "vps":
        session_manager.set_execution_target(user.id, "vps")
        await update.message.reply_text(
            "🖥️ 已切换到 *VPS 执行*\n\n任务将在 VPS 本地 Claude CLI 执行",
            parse_mode='Markdown'
        )

    elif new_target == "local":
        # 检查是否提供了 URL
        if len(args) > 1:
            new_url = args[1]
            # 简单校验 URL 格式
            if not new_url.startswith("http"):
                new_url = f"http://{new_url}"
            session_manager.set_local_node_url(user.id, new_url)
            session_manager.set_execution_target(user.id, "local")
            await update.message.reply_text(
                f"💻 已切换到 *本地节点执行*\n\n"
                f"节点地址: `{new_url}`\n\n"
                f"请确保本地已运行 Desktop API 且 Tailscale 已连接",
                parse_mode='Markdown'
            )
        elif current_url:
            # 使用已保存的 URL
            session_manager.set_execution_target(user.id, "local")
            await update.message.reply_text(
                f"💻 已切换到 *本地节点执行*\n\n"
                f"节点地址: `{current_url}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ 请提供本地节点 URL\n\n"
                "用法: `/target local http://100.x.x.x:2026`",
                parse_mode='Markdown'
            )

    elif new_target == "token":
        # 设置或清除 API Token
        if len(args) > 1:
            new_token = args[1]
            session_manager.set_local_node_token(user.id, new_token)
            await update.message.reply_text(
                "🔑 *API Token 已设置*\n\n"
                "本地节点请求将使用此 Token 进行认证",
                parse_mode='Markdown'
            )
        else:
            session_manager.set_local_node_token(user.id, None)
            await update.message.reply_text(
                "🔑 *API Token 已清除*",
                parse_mode='Markdown'
            )

    else:
        await update.message.reply_text(
            f"❌ 无效目标: {new_target}\n\n可用: `vps`, `local`, `token`",
            parse_mode='Markdown'
        )


async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换或查看当前项目（层级浏览）"""
    logger.info(f"收到 /project 命令: user={update.effective_user.id if update.effective_user else 'unknown'}")
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

    # 显示顶级项目/目录（层级浏览入口）
    top_items = claude_executor.get_top_level_items()
    keyboard = []

    for item in top_items:
        name = item["name"]
        path = item["path"]
        is_special = item.get("is_special", False)

        # 标记当前选中的项目
        prefix = "✅ " if path == current_project else ""

        if is_special:
            # default 特殊项目，直接选择
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}📌 {name}",
                    callback_data=f"select_project:{path}"
                )
            ])
        else:
            # 普通目录，可以进入浏览
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}📁 {name}",
                    callback_data=f"browse_dir:{path}"
                ),
                InlineKeyboardButton(
                    "✓ 选择",
                    callback_data=f"select_project:{path}"
                )
            ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    current_path = claude_executor.projects.get(current_project, "未知")

    await update.message.reply_text(
        f"📁 *项目选择*\n\n"
        f"当前项目: *{escape_markdown(current_project)}*\n"
        f"路径: `{current_path}`\n\n"
        f"💡 点击文件夹进入子目录，点击「✓ 选择」确认项目",
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
• /cron \\- 定时任务管理
"""

    await update.message.reply_text(
        settings_text,
        parse_mode='Markdown'
    )


async def cron_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """定时任务管理 - 一级入口"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    from ..services.cron_config import cron_config

    notify_enabled = cron_config.is_notification_enabled()
    notify_interval = cron_config.get_notification_interval()
    cron_tasks = cron_config.get_cron_tasks()
    pending_count = cron_config.get_pending_notifications_count()

    # 构建状态信息
    notify_status = "✅ 已开启" if notify_enabled else "❌ 已关闭"

    text = f"""⏰ *定时任务管理*

*Bot 通知*
状态: {notify_status}
检查间隔: 每 {notify_interval} 分钟
待发送: {pending_count} 条

*Cron 任务*
已配置: {len(cron_tasks)} 个任务
"""

    keyboard = [
        [
            InlineKeyboardButton(
                f"{'🔔' if notify_enabled else '🔕'} 通知开关",
                callback_data="cron_notify_toggle"
            ),
            InlineKeyboardButton(
                f"⏱️ 间隔 ({notify_interval}分)",
                callback_data="cron_notify_interval_menu"
            ),
        ],
        [InlineKeyboardButton("📋 任务列表", callback_data="cron_tasks_list")],
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
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
# 技能触发命令
# =====================================

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """触发 planning-with-files 技能"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📋 *Planning\\-with\\-Files 技能*\n\n"
            "用法: `/plan <任务描述>`\n\n"
            "功能:\n"
            "• 创建结构化任务计划 \\(task\\_plan\\.md\\)\n"
            "• 记录发现和中间结果 \\(findings\\.md\\)\n"
            "• 追踪执行进度 \\(progress\\.md\\)\n\n"
            "适用于复杂多步骤任务、研究项目、需要>5次工具调用的任务",
            parse_mode='MarkdownV2'
        )
        return

    prompt = " ".join(args)

    # 构建技能触发 prompt
    skill_prompt = f"/planning-with-files {prompt}"

    # 通过消息处理流程执行
    from .messages import handle_message

    # 通过 context.user_data 传递 prompt（避免修改不可变的 Message 对象）
    context.user_data['override_prompt'] = skill_prompt

    await handle_message(update, context)


async def ralph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """触发 ralph-loop 技能"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "🔄 *Ralph\\-Loop 技能*\n\n"
            "用法: `/ralph <任务描述> [\\-max N] [\\-completion TEXT]`\n\n"
            "参数:\n"
            "• `\\-max N`: 最大迭代次数 \\(默认 10\\)\n"
            "• `\\-completion TEXT`: 完成标记 \\(默认 COMPLETE\\)\n\n"
            "功能:\n"
            "• 自动迭代执行直到任务完成\n"
            "• 每次迭代继承上次结果继续改进\n"
            "• 适用于需要反复优化的复杂任务\n\n"
            "取消: `/cancel`",
            parse_mode='MarkdownV2'
        )
        return

    # 解析参数（支持多种格式）
    # 支持: -max 10, --max 10, - max 10（空格分隔）
    # 支持: -promise X, --promise X, - promise X, -completion X
    max_iterations = 10
    completion_promise = "COMPLETE"
    prompt_parts = []

    # 预处理第一步：拆分粘连的参数
    # 例如: "2。-max" -> ["2。", "-max"]
    # 例如: "文字-promise" -> ["文字", "-promise"]
    import re
    split_args = []
    param_pattern = re.compile(r'(-{1,2}(?:max|promise|completion|max-iterations|completion-promise))\b', re.IGNORECASE)
    for arg in args:
        # 检查是否有粘连的参数标记
        match = param_pattern.search(arg)
        if match and match.start() > 0:
            # 有粘连，拆分
            prefix = arg[:match.start()]
            suffix = arg[match.start():]
            if prefix:
                split_args.append(prefix)
            split_args.append(suffix)
        else:
            split_args.append(arg)

    # 预处理第二步：合并单独的 "-" 或 "--" 与后续 token
    # 例如: ["-", "max", "10"] -> ["-max", "10"]
    processed_args = []
    i = 0
    while i < len(split_args):
        arg = split_args[i]
        if arg in ("-", "--") and i + 1 < len(split_args):
            # 合并 "-" 或 "--" 与下一个 token
            next_arg = split_args[i + 1]
            if not next_arg.startswith("-"):
                processed_args.append(f"{arg}{next_arg}")
                i += 2
                continue
        processed_args.append(arg)
        i += 1

    # 解析处理后的参数
    i = 0
    while i < len(processed_args):
        arg = processed_args[i]
        # 支持 -max 和 --max
        if arg in ("-max", "--max", "--max-iterations") and i + 1 < len(processed_args):
            try:
                max_iterations = int(processed_args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        # 支持 -completion/-promise 和 --completion/--promise
        elif arg in ("-completion", "--completion", "-promise", "--promise", "--completion-promise") and i + 1 < len(processed_args):
            completion_promise = processed_args[i + 1]
            i += 2
            continue
        prompt_parts.append(processed_args[i])
        i += 1

    prompt = " ".join(prompt_parts)

    if not prompt:
        await update.message.reply_text("❌ 请提供任务描述")
        return

    # 构建技能调用 prompt
    # 明确指示使用 Skill 工具调用技能
    skill_args = f'{prompt} --max-iterations {max_iterations} --completion-promise "{completion_promise}"'
    skill_prompt = f'使用 Skill 工具调用技能，skill 参数为 "ralph-loop:ralph-loop"，args 参数为 "{skill_args}"'

    # 通过消息处理流程执行
    from .messages import handle_message

    # 通过 context.user_data 传递 prompt（避免修改不可变的 Message 对象）
    context.user_data['override_prompt'] = skill_prompt

    await handle_message(update, context)


async def cancel_ralph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消 ralph-loop"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    # 触发取消命令
    from .messages import handle_message
    context.user_data['override_prompt'] = "/cancel-ralph"
    await handle_message(update, context)


async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示技能菜单 - 点击即用"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    # 两列布局：技能按钮 + 信息按钮
    keyboard = [
        [
            InlineKeyboardButton("📋 Plan", callback_data="skill:plan:use"),
            InlineKeyboardButton("ℹ️", callback_data="skill:plan:info"),
        ],
        [
            InlineKeyboardButton("🔄 Ralph", callback_data="skill:ralph:use"),
            InlineKeyboardButton("ℹ️", callback_data="skill:ralph:info"),
        ],
        [
            InlineKeyboardButton("🎤 Transcribe", callback_data="skill:transcribe:info"),
            InlineKeyboardButton("ℹ️", callback_data="skill:transcribe:info"),
        ],
    ]

    await update.message.reply_text(
        "🛠️ *可用技能*\n\n"
        "点击技能名称直接使用，点击 ℹ️ 查看详情",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


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
    """取消当前任务（包括 Ralph Loop）"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    from ..services.task import task_manager
    import os
    import glob
    import subprocess

    cancelled_items = []

    # 1. 取消 task_manager 中的任务
    tasks = task_manager.get_user_tasks(user.id)
    for task in tasks:
        await task_manager.cancel_task(user.id, task.session_id)
        cancelled_items.append(f"任务 {task.session_id[:8] if task.session_id else 'unknown'}...")

    # 2. 查找并删除所有 ralph-loop.local.md 文件
    # 使用多个搜索路径确保能找到文件
    search_paths = [
        claude_executor.workspace_dir,  # workspace 目录
        claude_executor.work_dir,       # 工作目录
        claude_executor.get_user_project_dir(user.id),  # 用户当前项目目录
    ]

    # 去重
    search_paths = list(set(p for p in search_paths if p and os.path.exists(p)))

    ralph_files_found = set()
    for search_path in search_paths:
        # 搜索当前目录的 .claude 文件夹
        direct_file = os.path.join(search_path, '.claude', 'ralph-loop.local.md')
        if os.path.exists(direct_file):
            ralph_files_found.add(direct_file)

        # 递归搜索子目录
        ralph_files = glob.glob(f"{search_path}/**/.claude/ralph-loop.local.md", recursive=True)
        ralph_files_found.update(ralph_files)

    for ralph_file in ralph_files_found:
        try:
            # 读取迭代次数
            iteration = "unknown"
            with open(ralph_file, 'r') as f:
                file_content = f.read()
                for line in file_content.split('\n'):
                    if line.startswith('iteration:'):
                        iteration = line.split(':')[1].strip()
                        break

            os.remove(ralph_file)
            cancelled_items.append(f"Ralph Loop (迭代 {iteration})")
            logger.info(f"已删除 Ralph Loop 文件: {ralph_file}")
        except Exception as e:
            logger.error(f"删除 Ralph Loop 文件失败: {ralph_file}, 错误: {e}")

    # 3. 终止正在运行的 claude 进程
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude.*-p"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                pid = pid.strip()
                if pid and pid.isdigit():
                    try:
                        subprocess.run(["kill", pid], check=False)
                        cancelled_items.append(f"Claude 进程 (PID {pid})")
                        logger.info(f"已终止 Claude 进程: {pid}")
                    except Exception as e:
                        logger.error(f"终止进程失败: {pid}, 错误: {e}")
    except Exception as e:
        logger.error(f"查找 Claude 进程失败: {e}")

    if not cancelled_items:
        await update.message.reply_text("ℹ️ 没有正在运行的任务")
        return

    items_text = "\n".join([f"• {item}" for item in cancelled_items])
    await update.message.reply_text(f"✅ 已取消:\n{items_text}")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """清理当前会话上下文（保留会话名称）"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    # 获取当前活跃会话
    active_session_id = session_manager.get_active_session_id(user.id)

    if not active_session_id:
        await update.message.reply_text("ℹ️ 当前没有活跃会话")
        return

    # 获取会话信息
    session_data = session_manager.get_session(user.id, active_session_id)
    if not session_data:
        await update.message.reply_text("ℹ️ 会话不存在")
        return

    session_name = session_data.get("name", "未命名")

    # 清理会话上下文（删除旧会话，创建同名新会话）
    session_manager.clear_session_context(user.id, active_session_id)

    await update.message.reply_text(
        f"🧹 已清理会话上下文\n\n"
        f"会话: *{escape_markdown(session_name)}*\n"
        f"发送新消息开始全新对话",
        parse_mode='Markdown'
    )


# =====================================
# 记忆系统命令
# =====================================

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """记忆系统管理 - /memory [subcommand] [args]"""
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    memory_manager = get_memory_manager()
    if not memory_manager:
        await update.message.reply_text("❌ 记忆系统未初始化")
        return

    args = context.args

    # 无参数: 显示状态
    if not args:
        status_text = memory_manager.format_status()
        keyboard = [
            [
                InlineKeyboardButton("📖 学习模式", callback_data="memory:learn"),
                InlineKeyboardButton("🔍 搜索", callback_data="memory:search"),
            ],
            [
                InlineKeyboardButton("💾 保存记忆", callback_data="memory:save"),
                InlineKeyboardButton("🔄 同步到CLAUDE.md", callback_data="memory:sync"),
            ],
        ]
        await update.message.reply_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    subcommand = args[0].lower()

    # /memory learn [description] - 提取学习模式
    if subcommand == "learn":
        description = " ".join(args[1:]) if len(args) > 1 else None

        if not description:
            await update.message.reply_text(
                "📖 *提取学习模式*\n\n"
                "用法: `/memory learn <模式描述>`\n\n"
                "示例:\n"
                "• `/memory learn Python 3.9 类型注解兼容性`\n"
                "• `/memory learn Freqtrade 策略热更新方法`",
                parse_mode='Markdown'
            )
            return

        # 触发 Claude 来提取模式（通过消息处理流程）
        prompt = f"""请从当前会话中提取关于「{description}」的可复用模式，并保存到记忆系统。

提取要求:
1. 分析问题是什么
2. 解决方案是什么
3. 什么时候适用

然后调用记忆保存功能，将模式保存到 data/memory/learned/ 目录。"""

        from .messages import handle_message
        context.user_data['override_prompt'] = prompt
        await handle_message(update, context)
        return

    # /memory save <content> - 保存长期记忆
    if subcommand == "save":
        content = " ".join(args[1:]) if len(args) > 1 else None

        if not content:
            await update.message.reply_text(
                "💾 *保存长期记忆*\n\n"
                "用法: `/memory save <记忆内容>`\n\n"
                "示例:\n"
                "• `/memory save 用户偏好: 代码风格简洁`\n"
                "• `/memory save 项目架构: Bot -> Claude CLI -> 会话管理`",
                parse_mode='Markdown'
            )
            return

        # 解析 section (如果内容包含冒号，使用冒号前的部分作为 section)
        if ":" in content:
            section, value = content.split(":", 1)
            section = section.strip()
            value = value.strip()
        else:
            section = "杂项"
            value = content

        memory_manager.append_memory(section, value)
        await update.message.reply_text(
            f"✅ 已保存到长期记忆\n\n"
            f"分类: *{escape_markdown(section)}*\n"
            f"内容: {escape_markdown(value)}",
            parse_mode='Markdown'
        )
        return

    # /memory search <keyword> - 搜索记忆
    if subcommand == "search":
        keyword = " ".join(args[1:]) if len(args) > 1 else None

        if not keyword:
            await update.message.reply_text(
                "🔍 *搜索记忆*\n\n"
                "用法: `/memory search <关键词>`\n\n"
                "示例:\n"
                "• `/memory search freqtrade`\n"
                "• `/memory search 类型注解`",
                parse_mode='Markdown'
            )
            return

        results = memory_manager.search(keyword)

        if not results:
            await update.message.reply_text(f"🔍 未找到关于「{keyword}」的记忆")
            return

        # 格式化结果
        text = f"🔍 搜索「{escape_markdown(keyword)}」的结果:\n\n"
        for result in results[:5]:  # 最多显示 5 个文件
            text += f"📄 *{escape_markdown(result['file'])}*\n"
            for match in result['matches'][:3]:  # 每个文件最多 3 行
                text += f"  L{match['line']}: {escape_markdown(match['text'][:60])}...\n"
            text += "\n"

        await update.message.reply_text(text, parse_mode='Markdown')
        return

    # /memory sync - 同步到 CLAUDE.md
    if subcommand == "sync":
        # 触发 Claude 来同步记忆到 CLAUDE.md
        prompt = """请将记忆系统中的关键信息同步到项目的 CLAUDE.md 文件。

同步策略:
1. 读取 data/memory/MEMORY.md 中的用户偏好和项目知识
2. 读取 data/memory/learned/ 中的高频使用模式
3. 将核心信息整理后追加到 CLAUDE.md 的相应 section

注意:
- 只同步真正重要的、会频繁使用的信息
- 避免重复（检查 CLAUDE.md 中是否已存在）
- 保持 CLAUDE.md 的简洁性"""

        from .messages import handle_message
        context.user_data['override_prompt'] = prompt
        await handle_message(update, context)
        return

    # /memory index - 更新索引
    if subcommand == "index":
        memory_manager._update_index()
        await update.message.reply_text("✅ 已更新记忆索引")
        return

    # /memory archive - 归档旧记忆
    if subcommand == "archive":
        archived = memory_manager.archive_old_daily()
        await update.message.reply_text(f"✅ 已归档 {archived} 个旧的每日记忆文件")
        return

    # /memory forget [--confirm] - 遗忘低价值记忆
    if subcommand == "forget":
        confirm = "--confirm" in args or "-y" in args

        if not confirm:
            # 预览模式
            preview = memory_manager.get_forget_preview(threshold=25.0)
            await update.message.reply_text(
                f"🧹 *记忆遗忘预览*\n\n{preview}",
                parse_mode='Markdown'
            )
            return

        # 执行遗忘
        deleted = memory_manager.forget(auto=True, threshold=25.0, dry_run=False)

        if deleted:
            await update.message.reply_text(
                f"🧹 已遗忘 {len(deleted)} 个低价值记忆:\n" +
                "\n".join([f"• {d.split('/')[-1]}" for d in deleted])
            )
        else:
            await update.message.reply_text("没有需要遗忘的低价值记忆")
        return

    # 未知子命令
    await update.message.reply_text(
        "❓ 未知的子命令\n\n"
        "可用命令:\n"
        "• `/memory` - 查看状态\n"
        "• `/memory learn <描述>` - 提取学习模式\n"
        "• `/memory save <内容>` - 保存长期记忆\n"
        "• `/memory search <关键词>` - 搜索记忆\n"
        "• `/memory sync` - 同步到 CLAUDE.md\n"
        "• `/memory index` - 更新索引\n"
        "• `/memory archive` - 归档旧记忆\n"
        "• `/memory forget` - 遗忘低价值记忆",
        parse_mode='Markdown'
    )


# =====================================
# SEO 关键词挖掘命令
# =====================================

async def seo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    SEO 关键词挖掘技能

    用法:
    - /seo                     查看帮助和状态
    - /seo <领域> [方向]        执行关键词挖掘
    - /seo video               AI 视频方向挖掘
    - /seo image               AI 图片方向挖掘
    - /seo agent               AI Agent 方向挖掘
    - /seo report              查看历史报告
    """
    user = update.effective_user

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 未授权用户")
        return

    args = context.args

    # 无参数: 显示帮助和快捷按钮
    if not args:
        keyboard = [
            [
                InlineKeyboardButton("🎬 AI Video", callback_data="seo:video"),
                InlineKeyboardButton("🖼️ AI Image", callback_data="seo:image"),
            ],
            [
                InlineKeyboardButton("🤖 AI Agent", callback_data="seo:agent"),
                InlineKeyboardButton("✍️ AI Writing", callback_data="seo:writing"),
            ],
            [
                InlineKeyboardButton("💻 AI Code", callback_data="seo:code"),
                InlineKeyboardButton("📊 历史报告", callback_data="seo:report"),
            ],
        ]

        await update.message.reply_text(
            "🔍 *SEO 关键词挖掘*\n\n"
            "*快捷挖掘:* 点击下方按钮\n\n"
            "*自定义挖掘:*\n"
            "`/seo <领域描述>`\n\n"
            "*示例:*\n"
            "• `/seo ai video generator`\n"
            "• `/seo midjourney alternatives`\n"
            "• `/seo ai agent tools 2025`\n\n"
            "*挖掘流程:*\n"
            "1️⃣ 种子词扩展 (修饰词矩阵)\n"
            "2️⃣ SERP 分析 (竞争度评估)\n"
            "3️⃣ 机会评分 (蓝海词识别)\n"
            "4️⃣ 内容规划 (优先级建议)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # /seo report - 查看历史报告
    if args[0].lower() == "report":
        from ..services.skills import keyword_mining_manager
        if not keyword_mining_manager:
            await update.message.reply_text("❌ 关键词挖掘服务未初始化")
            return

        project_dir = claude_executor.get_user_project_dir(user.id)
        status = keyword_mining_manager.get_mining_status(project_dir)

        if not status or not status.get('reports'):
            await update.message.reply_text("📭 暂无历史报告\n\n使用 `/seo <领域>` 开始挖掘", parse_mode='Markdown')
            return

        text = "📊 *历史挖掘报告*\n\n"
        for report in status['reports'][:10]:
            text += f"• `{report['filename']}` ({report['modified']})\n"

        await update.message.reply_text(text, parse_mode='Markdown')
        return

    # 执行关键词挖掘
    user_prompt = " ".join(args)

    # 导入并使用 keyword_mining_manager
    from ..services.skills import keyword_mining_manager
    if not keyword_mining_manager:
        await update.message.reply_text("❌ 关键词挖掘服务未初始化")
        return

    # 解析 niche 和 direction
    niche, direction = keyword_mining_manager.parse_niche_from_prompt(user_prompt)

    # 构建挖掘 prompt
    mining_prompt = keyword_mining_manager.build_mining_prompt(
        user_prompt=user_prompt,
        niche=niche,
        direction=direction
    )

    # 通过消息处理流程执行
    from .messages import handle_message
    context.user_data['override_prompt'] = mining_prompt

    await handle_message(update, context)


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
        CommandHandler("target", target_command),  # 执行目标切换
        CommandHandler("project", project_command),
        CommandHandler("settings", settings_command),
        CommandHandler("cron", cron_command),
        CommandHandler("run", run_command),
        CommandHandler("status", status_command),
        CommandHandler("cancel", cancel_command),
        CommandHandler("clear", clear_command),
        # 技能触发命令
        CommandHandler("skills", skills_command),
        CommandHandler("plan", plan_command),
        CommandHandler("ralph", ralph_command),
        CommandHandler("cancel_ralph", cancel_ralph_command),
        # 记忆系统
        CommandHandler("memory", memory_command),
        # 关键词挖掘
        CommandHandler("seo", seo_command),
        CommandHandler("keywords", seo_command),  # 别名
    ]
