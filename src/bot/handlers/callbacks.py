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

        # 设置项目（旧版兼容）
        elif data.startswith("set_project:"):
            await _handle_set_project(query, user_id, data)

        # 浏览目录（层级浏览）
        elif data.startswith("browse_dir:"):
            await _handle_browse_dir(query, user_id, data)

        # 选择项目（显示确认）
        elif data.startswith("select_project:"):
            await _handle_select_project(query, user_id, data)

        # 确认项目选择
        elif data.startswith("confirm_project:"):
            await _handle_confirm_project(query, user_id, data)

        # 返回项目根目录
        elif data == "back_project_root":
            await _handle_back_project_root(query, user_id)

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

        # Cron 管理菜单
        elif data == "cron_menu":
            await _handle_cron_menu(query, user_id)

        elif data == "cron_notify_toggle":
            await _handle_cron_notify_toggle(query, user_id)

        elif data.startswith("cron_notify_interval:"):
            await _handle_cron_notify_interval(query, user_id, data)

        elif data == "cron_notify_interval_menu":
            await _handle_cron_notify_interval_menu(query, user_id)

        elif data.startswith("cron_task_toggle:"):
            await _handle_cron_task_toggle(query, user_id, data)

        elif data.startswith("cron_task_delete:"):
            await _handle_cron_task_delete(query, user_id, data)

        elif data.startswith("cron_task_delete_confirm:"):
            await _handle_cron_task_delete_confirm(query, user_id, data)

        elif data.startswith("cron_task_schedule:"):
            await _handle_cron_task_schedule_menu(query, user_id, data)

        elif data.startswith("cron_task_set_schedule:"):
            await _handle_cron_task_set_schedule(query, user_id, data)

        elif data == "cron_tasks_list":
            await _handle_cron_tasks_list(query, user_id)

        # 执行目标切换
        elif data.startswith("set_target:"):
            await _handle_set_target(query, user_id, data)

        # 转录模版选择
        elif data.startswith("transcribe_tpl:"):
            await _handle_transcribe_template(update, query, context, user_id, data)

        # 转录自定义提示
        elif data.startswith("transcribe_custom:"):
            await _handle_transcribe_custom(query, context, user_id, data)

        # SEO 关键词挖掘
        elif data.startswith("seo:"):
            await _handle_seo_callback(query, context, user_id, data)

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


async def _handle_browse_dir(query, user_id: int, data: str):
    """处理浏览目录（层级浏览）"""
    relative_path = data.split(":", 1)[1]

    # 获取目录内容
    dir_info = claude_executor.get_directory_contents(relative_path)
    current_path = dir_info["current_path"]
    parent_path = dir_info["parent_path"]
    dirs = dir_info["dirs"]
    can_select = dir_info["can_select"]

    current_project = session_manager.get_user_project(user_id)

    # 构建按钮
    keyboard = []

    # 返回上级按钮
    if parent_path is not None:
        if parent_path == "":
            keyboard.append([
                InlineKeyboardButton("⬆️ 返回根目录", callback_data="back_project_root")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(f"⬆️ 返回上级", callback_data=f"browse_dir:{parent_path}")
            ])

    # 子目录列表
    for d in dirs:
        name = d["name"]
        path = d["path"]
        prefix = "✅ " if path == current_project else ""

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

    # 如果当前目录可以作为项目选择（有内容但没有子目录）
    if can_select and not dirs:
        keyboard.append([
            InlineKeyboardButton(
                "✓ 选择当前目录",
                callback_data=f"select_project:{current_path}"
            )
        ])

    # 如果目录为空
    if not dirs and not can_select:
        keyboard.append([
            InlineKeyboardButton("📭 空目录", callback_data="noop")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📂 浏览: `{current_path or '/'}`\n\n"
        f"点击 📁 进入子目录，点击 ✓ 选择项目",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _handle_select_project(query, user_id: int, data: str):
    """处理选择项目（显示确认对话框）"""
    project = data.split(":", 1)[1]

    current_project = session_manager.get_user_project(user_id)
    project_dir = claude_executor.get_project_dir(project)

    # 构建确认信息
    is_same = project == current_project
    if is_same:
        message = (
            f"📌 当前项目: *{project}*\n"
            f"工作目录: `{project_dir}`\n\n"
            f"_这已经是当前活跃项目_"
        )
        keyboard = [[
            InlineKeyboardButton("⬅️ 返回", callback_data="back_project_root")
        ]]
    else:
        message = (
            f"🔄 确认切换到项目?\n\n"
            f"项目: *{project}*\n"
            f"工作目录: `{project_dir}`\n\n"
            f"⚠️ 切换项目将归档当前会话"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认切换", callback_data=f"confirm_project:{project}"),
                InlineKeyboardButton("❌ 取消", callback_data="back_project_root")
            ]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def _handle_confirm_project(query, user_id: int, data: str):
    """处理确认项目选择"""
    project = data.split(":", 1)[1]

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


async def _handle_back_project_root(query, user_id: int):
    """处理返回项目根目录"""
    current_project = session_manager.get_user_project(user_id)

    # 获取顶级项目列表
    top_items = claude_executor.get_top_level_items()

    keyboard = []
    for item in top_items:
        name = item["name"]
        path = item["path"]
        is_special = item.get("is_special", False)
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

    await query.edit_message_text(
        f"📂 选择项目\n当前: *{current_project}*\n\n"
        f"点击 📁 进入子目录，点击 ✓ 选择项目",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


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
    if len(parts) < 3 or not parts[2]:
        await query.edit_message_text("⚠️ 无效的数据")
        return

    try:
        target_user_id = int(parts[2])
    except ValueError:
        await query.edit_message_text("⚠️ 无效的用户ID")
        return

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

    elif skill_name == "transcribe":
        # Transcribe 只有 info，因为触发靠发送音频
        text = (
            "🎤 *Transcribe*\n\n"
            "*功能:*\n"
            "• 语音/音频文件转录为文字\n"
            "• 支持多种加工模版整理\n"
            "• 支持自定义提示词加工\n\n"
            "*使用方式:*\n"
            "• 直接发送语音消息\n"
            "• 发送音频文件 \\(mp3/m4a/wav等\\)\n"
            "• 转录后选择加工模版\n\n"
            "*可用模版:*\n"
            "📋 会议纪要 \\| 📝 内容摘要\n"
            "✅ 待办提取 \\| 📰 文章整理\n"
            "📄 仅转录 \\| ✏️ 自定义提示"
        )
        keyboard = [[
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
            [
                InlineKeyboardButton("🎤 Transcribe", callback_data="skill:transcribe:info"),
                InlineKeyboardButton("ℹ️", callback_data="skill:transcribe:info"),
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


# =====================================
# Cron 管理回调处理
# =====================================

async def _handle_cron_menu(query, user_id: int):
    """显示 Cron 管理主菜单"""
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

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def _handle_cron_notify_toggle(query, user_id: int):
    """切换通知开关"""
    from ..services.cron_config import cron_config
    from ..services.cron_notifier import cron_notifier

    current = cron_config.is_notification_enabled()
    cron_config.set_notification_enabled(not current)

    new_status = "✅ 已开启" if not current else "❌ 已关闭"

    # 如果从关闭变为开启，立即发送积压的消息
    if not current and cron_notifier:
        # 在后台立即处理待发送消息
        import asyncio
        asyncio.create_task(cron_notifier._process_pending_outputs())
        await query.answer(f"通知 {new_status}，正在发送积压消息...")
    else:
        await query.answer(f"通知 {new_status}")

    # 刷新菜单
    await _handle_cron_menu(query, user_id)


async def _handle_cron_notify_interval_menu(query, user_id: int):
    """显示通知间隔选择菜单"""
    from ..services.cron_config import cron_config

    current_interval = cron_config.get_notification_interval()

    text = f"""⏱️ *通知检查间隔*

当前: 每 {current_interval} 分钟

选择新的间隔:"""

    intervals = [5, 10, 15, 30, 60, 120]
    keyboard = []
    row = []

    for interval in intervals:
        prefix = "✅ " if interval == current_interval else ""
        label = f"{interval}分" if interval < 60 else f"{interval // 60}小时"
        row.append(InlineKeyboardButton(
            f"{prefix}{label}",
            callback_data=f"cron_notify_interval:{interval}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="cron_menu")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def _handle_cron_notify_interval(query, user_id: int, data: str):
    """设置通知间隔"""
    from ..services.cron_config import cron_config

    interval = int(data.split(":")[1])
    cron_config.set_notification_interval(interval)

    await query.answer(f"已设置为每 {interval} 分钟")

    # 返回主菜单
    await _handle_cron_menu(query, user_id)


async def _handle_cron_tasks_list(query, user_id: int):
    """显示 Cron 任务列表"""
    from ..services.cron_config import cron_config

    tasks = cron_config.get_cron_tasks()

    if not tasks:
        text = """📋 *Cron 任务列表*

暂无定时任务

💡 使用 `/cron add` 添加任务"""

        keyboard = [[InlineKeyboardButton("◀️ 返回", callback_data="cron_menu")]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    text = f"""📋 *Cron 任务列表*

共 {len(tasks)} 个任务:
"""

    keyboard = []
    for task in tasks:
        line_num = task["line_num"]
        description = task["description"]
        task_id = task.get("task_id") or f"task_{line_num}"
        enabled = task.get("enabled", True)

        # 显示任务名称（从命令中提取）
        command = task["command"]
        if "check_trading" in command:
            task_name = "Trading 检查"
        elif "scripts/cron/" in command:
            import re
            match = re.search(r'scripts/cron/(\w+)\.sh', command)
            task_name = match.group(1) if match else f"任务 {line_num}"
        else:
            task_name = f"任务 {line_num}"

        status_icon = "✅" if enabled else "⏸️"

        text += f"\n{status_icon} *{task_name}* \\- {description}"

        # 任务操作按钮
        keyboard.append([
            InlineKeyboardButton(
                f"{'⏸️' if enabled else '▶️'} {task_name[:10]}",
                callback_data=f"cron_task_toggle:{line_num}"
            ),
            InlineKeyboardButton("⏱️", callback_data=f"cron_task_schedule:{line_num}"),
            InlineKeyboardButton("🗑️", callback_data=f"cron_task_delete:{line_num}"),
        ])

    keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="cron_menu")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def _handle_cron_task_toggle(query, user_id: int, data: str):
    """切换任务开关（通过注释/取消注释实现）"""
    from ..services.cron_config import cron_config

    line_num = int(data.split(":")[1])
    tasks = cron_config.get_cron_tasks()

    # 找到对应任务
    target_task = None
    for task in tasks:
        if task["line_num"] == line_num:
            target_task = task
            break

    if not target_task:
        await query.answer("任务不存在")
        return

    task_id = target_task.get("task_id") or f"task_{line_num}"
    current_enabled = cron_config.is_task_enabled(task_id)

    # 切换状态
    cron_config.set_task_enabled(task_id, not current_enabled)

    new_status = "已启用" if not current_enabled else "已暂停"
    await query.answer(f"任务 {new_status}")

    # 刷新任务列表
    await _handle_cron_tasks_list(query, user_id)


async def _handle_cron_task_delete(query, user_id: int, data: str):
    """显示删除确认"""
    from ..services.cron_config import cron_config

    line_num = int(data.split(":")[1])
    tasks = cron_config.get_cron_tasks()

    # 找到对应任务
    target_task = None
    for task in tasks:
        if task["line_num"] == line_num:
            target_task = task
            break

    if not target_task:
        await query.answer("任务不存在")
        return

    text = f"""⚠️ *确认删除任务?*

执行周期: {target_task['description']}
命令: `{target_task['command'][:50]}...`

此操作不可恢复!"""

    keyboard = [
        [
            InlineKeyboardButton("✅ 确认删除", callback_data=f"cron_task_delete_confirm:{line_num}"),
            InlineKeyboardButton("❌ 取消", callback_data="cron_tasks_list"),
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def _handle_cron_task_delete_confirm(query, user_id: int, data: str):
    """确认删除任务"""
    from ..services.cron_config import cron_config

    line_num = int(data.split(":")[1])

    success = cron_config.remove_cron_task(line_num)

    if success:
        await query.answer("✅ 任务已删除")
    else:
        await query.answer("❌ 删除失败")

    # 返回任务列表
    await _handle_cron_tasks_list(query, user_id)


async def _handle_cron_task_schedule_menu(query, user_id: int, data: str):
    """显示任务周期修改菜单"""
    from ..services.cron_config import cron_config

    line_num = int(data.split(":")[1])
    tasks = cron_config.get_cron_tasks()

    # 找到对应任务
    target_task = None
    for task in tasks:
        if task["line_num"] == line_num:
            target_task = task
            break

    if not target_task:
        await query.answer("任务不存在")
        return

    text = f"""⏱️ *修改执行周期*

当前: {target_task['description']}

选择新的执行周期:"""

    # 常用周期选项
    schedules = [
        ("每5分钟", "*/5 * * * *"),
        ("每15分钟", "*/15 * * * *"),
        ("每30分钟", "*/30 * * * *"),
        ("每小时", "0 * * * *"),
        ("每2小时", "0 */2 * * *"),
        ("每天 00:00", "0 0 * * *"),
        ("每天 08:00", "0 8 * * *"),
        ("每天 12:00", "0 12 * * *"),
    ]

    keyboard = []
    for label, cron_expr in schedules:
        is_current = target_task["cron_expr"] == cron_expr
        prefix = "✅ " if is_current else ""
        keyboard.append([InlineKeyboardButton(
            f"{prefix}{label}",
            callback_data=f"cron_task_set_schedule:{line_num}:{cron_expr}"
        )])

    keyboard.append([InlineKeyboardButton("◀️ 返回", callback_data="cron_tasks_list")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def _handle_cron_task_set_schedule(query, user_id: int, data: str):
    """设置任务执行周期"""
    from ..services.cron_config import cron_config

    parts = data.split(":", 2)
    line_num = int(parts[1])
    new_cron_expr = parts[2]

    success = cron_config.update_cron_schedule(line_num, new_cron_expr)

    if success:
        await query.answer("✅ 执行周期已更新")
    else:
        await query.answer("❌ 更新失败")

    # 返回任务列表
    await _handle_cron_tasks_list(query, user_id)


async def _handle_set_target(query, user_id: int, data: str):
    """处理执行目标切换"""
    target = data.split(":", 1)[1]

    if target == "vps":
        session_manager.set_execution_target(user_id, "vps")
        await query.edit_message_text(
            "🖥️ 已切换到 *VPS 执行*\n\n任务将在 VPS 本地 Claude CLI 执行",
            parse_mode='Markdown'
        )

    elif target == "local":
        # 切换到本地节点（需要已有 URL 配置）
        current_url = session_manager.get_local_node_url(user_id)
        if current_url:
            session_manager.set_execution_target(user_id, "local")
            await query.edit_message_text(
                f"💻 已切换到 *本地节点执行*\n\n"
                f"节点地址: `{current_url}`",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ 请先设置本地节点 URL\n\n"
                "用法: `/target local http://100.x.x.x:2026`",
                parse_mode='Markdown'
            )

    elif target == "local_setup":
        # 提示用户设置本地节点
        await query.edit_message_text(
            "💻 *设置本地节点*\n\n"
            "请使用命令设置本地节点 URL:\n"
            "`/target local http://100.x.x.x:2026`\n\n"
            "可选设置认证 Token:\n"
            "`/target token <YOUR_TOKEN>`",
            parse_mode='Markdown'
        )

    else:
        await query.edit_message_text(f"❌ 无效目标: {target}")


# =====================================
# 转录模版回调处理
# =====================================

async def _handle_transcribe_template(update: Update, query, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: str):
    """
    处理转录模版选择回调

    回调数据格式: transcribe_tpl:{template_key}:{user_id}
    """
    from ..services.skills import transcribe_manager, TRANSCRIBE_TEMPLATES
    from .messages import handle_message

    parts = data.split(":")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ 无效的模版数据")
        return

    template_key = parts[1]

    # 获取暂存的转录文本
    transcribed_text = context.user_data.get('pending_transcription')
    if not transcribed_text:
        await query.edit_message_text("❌ 转录文本已过期，请重新发送音频")
        return

    template = TRANSCRIBE_TEMPLATES.get(template_key)
    if not template:
        await query.edit_message_text("⚠️ 未知的模版类型")
        return

    template_name = template["name"]

    # 仅转录模式：直接返回转录文本
    if template_key == "raw":
        # 清除暂存
        context.user_data.pop('pending_transcription', None)
        await query.edit_message_text(
            f"📄 转录文本：\n\n{transcribed_text}"
        )
        return

    # 构建加工 prompt
    process_prompt = transcribe_manager.build_process_prompt(template_key, transcribed_text)
    if not process_prompt:
        await query.edit_message_text("❌ 模版构建失败")
        return

    # 记录模版信息，用于加工完成后保存结果
    transcription_path = context.user_data.get('transcription_path', '')
    source_filename = "audio"
    if transcription_path:
        import os
        source_filename = os.path.basename(transcription_path)
    context.user_data['pending_save_template'] = {
        'template_name': template_name,
        'source_filename': source_filename,
    }

    # 清除暂存
    context.user_data.pop('pending_transcription', None)
    context.user_data.pop('transcription_path', None)

    # 更新消息显示正在加工
    await query.edit_message_text(
        f"{template['emoji']} 正在用「{template_name}」模版整理..."
    )

    # 通过 override_prompt 传入 handle_message 执行 Claude 加工
    # 注意: 此处 update 来自 callback query，update.message 为 None
    # handle_message 通过 update.callback_query.message 获取消息对象
    context.user_data['override_prompt'] = process_prompt
    await handle_message(update, context)


async def _handle_transcribe_custom(query, context: ContextTypes.DEFAULT_TYPE, user_id: int, data: str):
    """
    处理转录自定义提示回调

    设置 pending_skill，等待用户输入自定义 prompt
    """
    # 检查是否有暂存的转录文本
    transcribed_text = context.user_data.get('pending_transcription')
    if not transcribed_text:
        await query.edit_message_text("❌ 转录文本已过期，请重新发送音频")
        return

    # 设置待处理状态
    context.user_data['pending_skill'] = 'transcribe_custom'

    await query.edit_message_text(
        "✏️ *自定义加工*\n\n"
        "请直接发送您的提示词，例如：\n"
        "• 翻译成英文\n"
        "• 提取关键数据\n"
        "• 改写为正式商务风格\n\n"
        f"_转录文本 ({len(transcribed_text)} 字) 已暂存_",
        parse_mode='Markdown'
    )


# =====================================
# SEO 关键词挖掘回调处理
# =====================================

async def _handle_seo_callback(query, context, user_id: int, data: str):
    """处理 SEO 关键词挖掘回调"""
    from ..services.skills import keyword_mining_manager
    from .messages import handle_message

    parts = data.split(":")
    if len(parts) < 2:
        await query.edit_message_text("⚠️ 无效的操作")
        return

    action = parts[1]

    # 查看历史报告
    if action == "report":
        if not keyword_mining_manager:
            await query.edit_message_text("❌ 关键词挖掘服务未初始化")
            return

        project_dir = claude_executor.get_user_project_dir(user_id)
        status = keyword_mining_manager.get_mining_status(project_dir)

        if not status or not status.get('reports'):
            await query.edit_message_text(
                "📭 暂无历史报告\n\n使用 `/seo <领域>` 开始挖掘",
                parse_mode='Markdown'
            )
            return

        text = "📊 *历史挖掘报告*\n\n"
        for report in status['reports'][:10]:
            text += f"• `{report['filename']}` ({report['modified']})\n"

        keyboard = [[InlineKeyboardButton("◀️ 返回", callback_data="seo:menu")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # 返回主菜单
    if action == "menu":
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

        await query.edit_message_text(
            "🔍 *SEO 关键词挖掘*\n\n"
            "*快捷挖掘:* 点击下方按钮\n\n"
            "*自定义挖掘:*\n"
            "`/seo <领域描述>`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    # 各方向的挖掘配置
    direction_config = {
        "video": {
            "niche": "AI Tools",
            "direction": "video",
            "prompt": "挖掘 AI 视频生成工具相关的关键词机会，包括 text-to-video、image-to-video、视频编辑、Sora 替代品等方向"
        },
        "image": {
            "niche": "AI Tools",
            "direction": "image",
            "prompt": "挖掘 AI 图片生成工具相关的关键词机会，包括 text-to-image、图片编辑、Midjourney 替代品、AI 艺术生成等方向"
        },
        "agent": {
            "niche": "AI Tools",
            "direction": "agent",
            "prompt": "挖掘 AI Agent 工具相关的关键词机会，包括自动化工作流、AutoGPT 替代品、AI 助手、agentic AI 等方向"
        },
        "writing": {
            "niche": "AI Tools",
            "direction": "writing",
            "prompt": "挖掘 AI 写作工具相关的关键词机会，包括 AI 文案、博客生成、Jasper 替代品、内容创作工具等方向"
        },
        "code": {
            "niche": "AI Tools",
            "direction": "code",
            "prompt": "挖掘 AI 编程工具相关的关键词机会，包括代码生成、GitHub Copilot 替代品、AI 代码助手等方向"
        }
    }

    if action not in direction_config:
        await query.edit_message_text(f"⚠️ 未知的挖掘方向: {action}")
        return

    config = direction_config[action]

    # 更新消息显示进行中状态
    await query.edit_message_text(
        f"🔍 *正在挖掘 {action.upper()} 方向关键词...*\n\n"
        "请稍候，这可能需要一些时间...",
        parse_mode='Markdown'
    )

    # 构建挖掘 prompt
    if not keyword_mining_manager:
        await query.message.reply_text("❌ 关键词挖掘服务未初始化")
        return

    mining_prompt = keyword_mining_manager.build_mining_prompt(
        user_prompt=config["prompt"],
        niche=config["niche"],
        direction=config["direction"]
    )

    # 通过消息处理流程执行
    # 创建一个模拟的 update 对象来触发消息处理
    context.user_data['override_prompt'] = mining_prompt

    # 发送新消息触发处理
    await query.message.reply_text(
        f"🚀 开始挖掘 *{action.upper()}* 方向关键词...",
        parse_mode='Markdown'
    )

    # 实际执行需要通过消息处理器
    # 这里我们直接调用 claude_executor
    from ..services.claude import claude_executor

    try:
        output, _ = claude_executor.execute_sync(
            prompt=mining_prompt,
            session_id=None,
            user_id=user_id
        )

        # 分段发送结果（避免消息过长）
        from ...utils.formatters import safe_truncate
        output = safe_truncate(output, 4000)

        await query.message.reply_text(
            f"✅ *{action.upper()} 关键词挖掘完成*\n\n{output}",
            parse_mode=None  # 使用纯文本避免解析问题
        )

    except Exception as e:
        logger.error(f"关键词挖掘失败: {e}")
        await query.message.reply_text(f"❌ 挖掘失败: {str(e)[:200]}")


def get_callback_handlers():
    """返回回调处理器列表"""
    return [
        CallbackQueryHandler(button_callback)
    ]
