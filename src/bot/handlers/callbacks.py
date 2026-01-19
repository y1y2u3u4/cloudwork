"""
CloudWork Callback Query Handlers

处理 InlineKeyboardButton 的回调查询
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, CallbackQueryHandler

from ...utils.auth import is_authorized
from ...utils.formatters import format_session_info, safe_edit_message
from ..services.session import session_manager
from ..services.claude import claude_executor, AVAILABLE_MODELS, EXECUTION_MODES
from ..services.task import task_manager, TaskState

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    统一的回调查询处理器

    回调数据格式:
    - switch:{session_id} - 切换会话
    - restore:{session_id} - 恢复归档会话
    - set_model:{model} - 设置模型
    - set_mode:{mode} - 设置执行模式
    - set_project:{project} - 设置项目
    - answer_opt_{session_id}_{option_index} - 回答选项
    - custom_input_{session_id} - 自定义输入
    - confirm_plan_{session_id} - 确认计划
    - cancel_plan_{session_id} - 取消计划
    - cancel_task_{user_id} - 取消正在执行的任务
    - page_sessions_{page} - 会话分页
    - page_archived_{page} - 归档分页
    """
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user = update.effective_user
    if not user:
        return

    if not is_authorized(user.id):
        await query.edit_message_text("⛔ 您没有使用权限")
        return

    user_id = user.id
    data = query.data

    logger.info(f"回调查询: user={user_id}, data={data}")

    try:
        # 会话切换
        if data.startswith("switch:"):
            await _handle_switch_session(query, user_id, data)

        # 恢复归档会话
        elif data.startswith("restore:"):
            await _handle_restore_session(query, user_id, data)

        # 设置模型
        elif data.startswith("set_model:"):
            await _handle_set_model(query, user_id, data)

        # 设置执行模式
        elif data.startswith("set_mode:"):
            await _handle_set_mode(query, user_id, data)

        # 设置项目
        elif data.startswith("set_project:"):
            await _handle_set_project(query, user_id, data)

        # 回答 AskUserQuestion 选项
        elif data.startswith("answer_opt_"):
            await _handle_answer_option(query, user_id, data)

        # 自定义输入
        elif data.startswith("custom_input_"):
            await _handle_custom_input(query, user_id, data)

        # 确认计划
        elif data.startswith("confirm_plan_"):
            await _handle_confirm_plan(query, user_id, data)

        # 取消计划
        elif data.startswith("cancel_plan_"):
            await _handle_cancel_plan(query, user_id, data)

        # 会话分页
        elif data.startswith("page_sessions_"):
            await _handle_sessions_pagination(query, user_id, data)

        # 归档分页
        elif data.startswith("page_archived_"):
            await _handle_archived_pagination(query, user_id, data)

        # 取消任务
        elif data.startswith("cancel_task_"):
            await _handle_cancel_task(query, user_id, data)

        # 技能菜单
        elif data.startswith("skill:"):
            await _handle_skill_callback(query, context, user_id, data)

        else:
            logger.warning(f"未知的回调数据: {data}")

    except Exception as e:
        logger.error(f"回调处理错误: {e}")
        try:
            await query.edit_message_text(f"❌ 操作失败: {str(e)[:100]}")
        except Exception:
            pass


async def _handle_switch_session(query, user_id: int, data: str):
    """处理会话切换"""
    session_id = data.split(":", 1)[1]

    session_manager.set_active_session(user_id, session_id)
    session = session_manager.get_session(user_id, session_id)

    if session:
        session_name = session.get("name", "未命名")
        message_count = session.get("message_count", 0)
        await query.edit_message_text(
            f"✅ 已切换到会话: *{session_name}*\n"
            f"历史消息: {message_count} 条\n\n"
            f"现在可以直接发送消息继续对话",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("⚠️ 会话不存在或已过期")


async def _handle_restore_session(query, user_id: int, data: str):
    """处理恢复归档会话"""
    session_id = data.split(":", 1)[1]

    success = session_manager.restore_session(user_id, session_id)

    if success:
        session = session_manager.get_session(user_id, session_id)
        session_name = session.get("name", "未命名") if session else "未命名"
        await query.edit_message_text(
            f"✅ 已恢复会话: *{session_name}*\n\n"
            f"会话已设为活跃，可以直接发送消息继续对话",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("⚠️ 恢复会话失败，会话可能不存在")


async def _handle_set_model(query, user_id: int, data: str):
    """处理设置模型"""
    model = data.split(":", 1)[1]

    if model not in AVAILABLE_MODELS:
        await query.edit_message_text(f"⚠️ 无效的模型: {model}")
        return

    session_manager.set_user_model(user_id, model)
    model_desc = AVAILABLE_MODELS.get(model, model)

    await query.edit_message_text(
        f"✅ 已切换到模型: *{model}*\n"
        f"({model_desc})",
        parse_mode='Markdown'
    )


async def _handle_set_mode(query, user_id: int, data: str):
    """处理设置执行模式"""
    mode = data.split(":", 1)[1]

    if mode not in EXECUTION_MODES:
        await query.edit_message_text(f"⚠️ 无效的模式: {mode}")
        return

    session_manager.set_user_execution_mode(user_id, mode)
    mode_desc = EXECUTION_MODES.get(mode, mode)

    await query.edit_message_text(
        f"✅ 已切换到模式: *{mode}*\n"
        f"({mode_desc})",
        parse_mode='Markdown'
    )


async def _handle_set_project(query, user_id: int, data: str):
    """处理设置项目"""
    project = data.split(":", 1)[1]

    # 获取当前项目，检查是否真的切换了
    current_project = session_manager.get_user_project(user_id)

    # 如果切换到不同的项目，归档当前会话
    if project != current_project:
        current_session_id = session_manager.get_active_session_id(user_id)
        if current_session_id:
            session_manager.archive_session(user_id, current_session_id)
            logger.info(f"切换项目时归档会话: {current_session_id[:8]}...")

    session_manager.set_user_project(user_id, project)
    project_dir = claude_executor.get_project_dir(project)

    # 构建提示信息
    message = f"✅ 已切换到项目: *{project}*\n工作目录: `{project_dir}`"
    if project != current_project:
        message += "\n\n💡 已归档之前的会话，下次发消息将创建新会话"

    await query.edit_message_text(message, parse_mode='Markdown')


async def _handle_answer_option(query, user_id: int, data: str):
    """处理 AskUserQuestion 选项回答"""
    # 解析: answer_opt_{session_id}_{option_index}
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("⚠️ 无效的选项数据")
        return

    session_id_prefix = parts[2]
    option_index = int(parts[3])

    # 查找匹配的任务
    task = _find_task_by_session_prefix(user_id, session_id_prefix)
    if not task:
        await query.edit_message_text("⚠️ 未找到对应的任务，可能已超时")
        return

    # 获取选项文本
    options = task.question_options or []
    if option_index >= len(options):
        await query.edit_message_text("⚠️ 选项不存在")
        return

    selected_option = options[option_index]
    answer_text = selected_option.get("label", str(option_index))

    # 设置用户回复
    task.user_reply = answer_text
    task.state = TaskState.RUNNING
    if task.input_event:
        task.input_event.set()

    await query.edit_message_text(
        f"✅ 已选择: *{answer_text}*\n\n继续执行...",
        parse_mode='Markdown'
    )


async def _handle_custom_input(query, user_id: int, data: str):
    """处理自定义输入请求"""
    # 解析: custom_input_{session_id}
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的数据")
        return

    session_id_prefix = parts[2]

    task = _find_task_by_session_prefix(user_id, session_id_prefix)
    if not task:
        await query.edit_message_text("⚠️ 未找到对应的任务")
        return

    question = task.pending_question or "请输入您的回答"

    await query.edit_message_text(
        f"📝 请直接发送消息作为您的回答\n\n"
        f"问题: {question}\n\n"
        f"_直接发送文字消息即可_",
        parse_mode='Markdown'
    )


async def _handle_confirm_plan(query, user_id: int, data: str):
    """处理确认计划执行"""
    # 解析: confirm_plan_{session_id}
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的数据")
        return

    session_id = parts[2]

    plan = task_manager.get_pending_plan(user_id, session_id)
    if not plan:
        await query.edit_message_text("⚠️ 计划已过期或不存在")
        return

    # 移除待执行计划
    task_manager.remove_pending_plan(user_id, session_id)

    await query.edit_message_text("✅ 已确认，开始执行计划...")

    # TODO: 触发计划执行
    # 这里需要实际调用 claude_executor 执行
    logger.info(f"确认执行计划: user={user_id}, session={session_id}")


async def _handle_cancel_plan(query, user_id: int, data: str):
    """处理取消计划"""
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的数据")
        return

    session_id = parts[2]

    task_manager.remove_pending_plan(user_id, session_id)

    await query.edit_message_text("❌ 已取消计划")


async def _handle_cancel_task(query, user_id: int, data: str):
    """处理取消正在执行的任务"""
    # 解析: cancel_task_{user_id}
    parts = data.split("_")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的数据")
        return

    target_user_id = int(parts[2])

    # 安全检查：只能取消自己的任务
    if target_user_id != user_id:
        await query.edit_message_text("⚠️ 无法取消其他用户的任务")
        return

    # 获取当前活跃会话
    session_id = session_manager.get_active_session_id(user_id)

    # 尝试取消任务
    cancelled = await task_manager.cancel_task(user_id, session_id)

    if cancelled:
        await query.edit_message_text("⏹️ 已取消任务")
        logger.info(f"用户 {user_id} 通过按钮取消了任务")
    else:
        await query.edit_message_text("⚠️ 没有正在执行的任务")


async def _handle_sessions_pagination(query, user_id: int, data: str):
    """处理会话列表分页"""
    page = int(data.split("_")[2])
    page_size = 5

    sessions = session_manager.get_sessions(user_id)
    active_id = session_manager.get_active_session_id(user_id)

    total_pages = (len(sessions) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_sessions = sessions[start_idx:end_idx]

    if not page_sessions:
        await query.edit_message_text("📭 没有更多会话")
        return

    # 构建按钮
    keyboard = []
    for session in page_sessions:
        session_id = session.get("id", "")
        is_active = session_id == active_id
        info = format_session_info(session, is_active)
        keyboard.append([
            InlineKeyboardButton(info, callback_data=f"switch:{session_id}")
        ])

    # 分页按钮
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ 上一页", callback_data=f"page_sessions_{page - 1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("下一页 ▶️", callback_data=f"page_sessions_{page + 1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📋 会话列表 (第 {page + 1}/{total_pages} 页)\n"
        f"点击切换到对应会话:",
        reply_markup=reply_markup
    )


async def _handle_archived_pagination(query, user_id: int, data: str):
    """处理归档会话列表分页"""
    page = int(data.split("_")[2])
    page_size = 5

    archived = session_manager.get_archived_sessions(user_id)
    total_pages = (len(archived) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_archived = archived[start_idx:end_idx]

    if not page_archived:
        await query.edit_message_text("📭 没有更多归档会话")
        return

    # 构建按钮
    keyboard = []
    for session in page_archived:
        session_id = session.get("id", "")
        info = format_session_info(session, False)
        keyboard.append([
            InlineKeyboardButton(f"🗄️ {info}", callback_data=f"restore:{session_id}")
        ])

    # 分页按钮
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ 上一页", callback_data=f"page_archived_{page - 1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("下一页 ▶️", callback_data=f"page_archived_{page + 1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🗄️ 归档会话 (第 {page + 1}/{total_pages} 页)\n"
        f"点击恢复会话:",
        reply_markup=reply_markup
    )


def _find_task_by_session_prefix(user_id: int, session_id_prefix: str):
    """通过会话 ID 前缀查找任务"""
    tasks = task_manager.get_user_tasks(user_id)
    for task in tasks:
        if task.session_id and task.session_id.startswith(session_id_prefix):
            return task
    return None


async def _handle_skill_callback(query, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: str):
    """处理技能按钮回调"""
    parts = data.split(":")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的技能数据")
        return

    skill_name = parts[1]  # plan 或 ralph
    action = parts[2]      # use 或 info

    if skill_name == "plan":
        if action == "use":
            # 存储等待状态，消息处理器会检测这个状态
            context.user_data['pending_skill'] = 'plan'
            # 发送新消息并强制回复
            await query.message.reply_text(
                "📋 *Planning\\-with\\-Files*\n\n请直接输入任务描述:",
                parse_mode='MarkdownV2',
                reply_markup=ForceReply(selective=True, input_field_placeholder="/plan 你的任务描述")
            )
            await query.answer()
            return
        else:  # info
            text = (
                "📋 *Planning\\-with\\-Files*\n\n"
                "*功能:*\n"
                "• 创建 task\\_plan\\.md \\- 任务计划\n"
                "• 创建 findings\\.md \\- 发现记录\n"
                "• 创建 progress\\.md \\- 进度追踪\n\n"
                "*适用场景:*\n"
                "• 复杂多步骤任务\n"
                "• 研究项目\n"
                "• 需要 \>5 次工具调用的任务"
            )
            keyboard = [[
                InlineKeyboardButton("▶️ 使用", callback_data="skill:plan:use"),
                InlineKeyboardButton("◀️ 返回", callback_data="skill:back:menu")
            ]]

    elif skill_name == "ralph":
        if action == "use":
            # 存储等待状态
            context.user_data['pending_skill'] = 'ralph'
            # 发送新消息并强制回复
            await query.message.reply_text(
                "🔄 *Ralph\\-Loop*\n\n请直接输入任务描述:\n\\(可选: 添加 `\\-\\-max N` 设置最大迭代次数\\)",
                parse_mode='MarkdownV2',
                reply_markup=ForceReply(selective=True, input_field_placeholder="/ralph 你的任务描述")
            )
            await query.answer()
            return
        else:  # info
            text = (
                "🔄 *Ralph\\-Loop*\n\n"
                "*功能:*\n"
                "• 自动迭代执行直到任务完成\n"
                "• 每次迭代继承上次结果\n"
                "• 输出完成标记时自动停止\n\n"
                "*参数:*\n"
                "• `\\-\\-max N` \\- 最大迭代次数 \\(默认 10\\)\n"
                "• `\\-\\-promise TEXT` \\- 完成标记"
            )
            keyboard = [[
                InlineKeyboardButton("▶️ 使用", callback_data="skill:ralph:use"),
                InlineKeyboardButton("◀️ 返回", callback_data="skill:back:menu")
            ]]

    elif skill_name == "back":
        # 返回技能列表
        keyboard = [
            [
                InlineKeyboardButton("📋 Plan", callback_data="skill:plan:use"),
                InlineKeyboardButton("ℹ️", callback_data="skill:plan:info"),
            ],
            [
                InlineKeyboardButton("🔄 Ralph", callback_data="skill:ralph:use"),
                InlineKeyboardButton("ℹ️", callback_data="skill:ralph:info"),
            ],
        ]
        text = "🛠️ *可用技能*\n\n点击技能名称直接使用，点击 ℹ️ 查看详情"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    else:
        await query.edit_message_text("⚠️ 未知的技能")
        return

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )


def get_callback_handlers():
    """返回回调处理器列表"""
    return [
        CallbackQueryHandler(button_callback)
    ]
