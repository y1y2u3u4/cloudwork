"""
CloudWork Message Handlers

处理用户直接发送的文本消息（非命令）
"""

import logging
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from ...utils.auth import is_authorized
from ...utils.formatters import (
    format_claude_output,
    format_progress_text,
    safe_edit_message,
    generate_session_name,
    strip_ansi_codes,
    split_long_message
)
from ..services.session import session_manager
from ..services.claude import claude_executor
from ..services.task import task_manager, TaskState

logger = logging.getLogger(__name__)

# 消息 ID 到会话 ID 的映射（用于回复消息时自动切换会话）
message_session_map: dict = {}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户直接发送的文本消息

    支持:
    - 在当前活跃会话中对话
    - 回复历史消息自动切换到该会话
    - 自动创建新会话（如果没有活跃会话）
    """
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    if not user:
        return

    # 权限检查
    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 您没有使用权限")
        return

    user_id = user.id
    chat_id = update.effective_chat.id
    prompt = update.message.text.strip()

    if not prompt:
        return

    logger.info(f"收到消息: user={user_id}, text={prompt[:50]}...")

    # 检查是否回复了某条消息（自动切换会话）
    session_id = await _handle_reply_session_switch(update, user_id)

    # 如果没有通过回复切换，使用当前活跃会话
    if not session_id:
        session_id = session_manager.get_active_session_id(user_id)

    # 检查是否有运行中的任务
    if task_manager.has_running_task(user_id, session_id):
        # 检查是否在等待用户输入
        if task_manager.is_waiting_input(user_id, session_id):
            # 设置用户回复
            task_manager.set_user_reply(user_id, session_id, prompt)
            await update.message.reply_text("✅ 已收到您的回复，继续执行...")
            return
        else:
            await update.message.reply_text(
                "⏳ 有任务正在执行中，请等待完成或使用 /cancel 取消"
            )
            return

    # 发送初始状态消息
    status_message = await update.message.reply_text("🚀 正在启动 Claude...")

    # 如果没有活跃会话，创建新会话
    if not session_id:
        session_name = generate_session_name(prompt)
        pending_session_id = session_manager.generate_pending_session_id(user_id)
        session = session_manager.create_session(user_id, pending_session_id, name=session_name)
        session_id = session.id
        logger.info(f"自动创建新会话: {session_id[:8]}...")

    # 记录消息到会话的映射
    message_session_map[status_message.message_id] = session_id

    # 定义进度回调
    async def progress_callback(text: str, status: Optional[str]):
        """更新进度消息"""
        try:
            progress_text = format_progress_text(text, status=status)
            await safe_edit_message(status_message, progress_text, parse_mode=None)
        except Exception as e:
            logger.warning(f"更新进度消息失败: {e}")

    # 定义问题回调（用于 AskUserQuestion）
    async def question_callback(question_block: dict, task):
        """处理 Claude 的 AskUserQuestion"""
        await _handle_ask_user_question(
            update, context, question_block, task, session_id
        )

    try:
        # 执行 Claude
        output, new_session_id = await claude_executor.execute_stream(
            prompt=prompt,
            session_id=session_id,
            user_id=user_id,
            chat_id=chat_id,
            message_id=status_message.message_id,
            progress_callback=progress_callback,
            question_callback=question_callback
        )

        # 更新会话 ID（如果是新会话）
        if new_session_id and new_session_id != session_id:
            # 检查旧会话是否仍然存在（可能在重试时被删除）
            old_session = session_manager.get_session(user_id, session_id)
            if old_session:
                # 旧会话存在，正常更新 ID
                session_manager.update_session_id(user_id, session_id, new_session_id)
            else:
                # 旧会话不存在（可能已失效被删除），创建全新会话
                new_session_name = generate_session_name(prompt)
                session_manager.create_session(user_id, new_session_id, name=new_session_name)
                logger.info(f"旧会话已失效，创建全新会话: {new_session_id[:8]}...")
            session_id = new_session_id
            message_session_map[status_message.message_id] = session_id

        # 更新会话活跃时间和消息计数
        session_manager.touch_session(user_id, session_id)

        # 分段发送长输出
        segments = split_long_message(output)

        if len(segments) == 1:
            # 单段消息，直接编辑原消息
            formatted_output, parse_mode = format_claude_output(segments[0])
            await safe_edit_message(status_message, formatted_output, parse_mode=parse_mode)
        else:
            # 多段消息，编辑第一条，发送其余
            first_segment, parse_mode = format_claude_output(segments[0])
            await safe_edit_message(status_message, first_segment, parse_mode=parse_mode)

            # 发送其余段落
            for segment in segments[1:]:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=segment,
                        parse_mode=None,  # 纯文本避免解析错误
                        reply_to_message_id=status_message.message_id
                    )
                except Exception as e:
                    logger.warning(f"发送分段消息失败: {e}")

        # 发送完成通知（新消息，触发推送通知）
        session_info = session_manager.get_session(user_id, session_id)
        session_name = session_info.get("name", "未命名") if session_info else "未命名"
        message_count = session_info.get("message_count", 1) if session_info else 1
        complete_time = datetime.now().strftime("%H:%M:%S")

        # 获取项目和模型信息
        current_project = session_manager.get_user_project(user_id)
        current_model = session_manager.get_user_model(user_id)

        # 构建完成通知文本
        notify_text = (
            f"✅ 任务完成 | {complete_time}\n"
            f"💬 {session_name} · 第 {message_count} 次对话\n"
            f"📁 {current_project} · 🤖 {current_model}"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=notify_text,
            reply_to_message_id=status_message.message_id
        )

        logger.info(f"消息处理完成: user={user_id}, session={session_id[:8]}...")

    except Exception as e:
        logger.error(f"消息处理错误: {e}")
        await safe_edit_message(
            status_message,
            f"❌ 执行出错: {str(e)[:200]}",
            parse_mode=None
        )


async def _handle_reply_session_switch(
    update: Update,
    user_id: int
) -> Optional[str]:
    """
    处理回复消息时的会话切换

    如果用户回复了某条历史消息，自动切换到该消息所属的会话
    """
    if not update.message.reply_to_message:
        return None

    reply_msg_id = update.message.reply_to_message.message_id

    # 从映射中查找会话 ID
    if reply_msg_id in message_session_map:
        session_id = message_session_map[reply_msg_id]
        # 切换到该会话
        session_manager.set_active_session(user_id, session_id)
        logger.info(f"通过回复消息切换会话: {session_id[:8]}...")
        return session_id

    return None


async def _handle_ask_user_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question_block: dict,
    task,
    session_id: str
):
    """
    处理 Claude 的 AskUserQuestion 工具调用

    显示问题和选项按钮，等待用户选择
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    try:
        # 解析问题内容
        input_data = question_block.get("input", {})
        questions = input_data.get("questions", [])

        if not questions:
            logger.warning("AskUserQuestion 没有问题内容")
            return

        # 设置任务状态为等待输入
        task.state = TaskState.WAITING_INPUT

        # 构建消息文本
        message_parts = ["🤔 **Claude 需要您的输入**\n"]

        for i, q in enumerate(questions):
            question_text = q.get("question", "")
            header = q.get("header", "")
            options = q.get("options", [])

            if header:
                message_parts.append(f"**{header}**")
            message_parts.append(f"{question_text}\n")

            # 保存选项到任务
            task.pending_question = question_text
            task.question_options = options

        message_text = "\n".join(message_parts)

        # 构建选项按钮
        keyboard = []
        first_question = questions[0] if questions else {}
        options = first_question.get("options", [])

        for idx, opt in enumerate(options):
            label = opt.get("label", f"选项 {idx + 1}")
            # 回调数据格式: answer_opt_{session_id}_{option_index}
            callback_data = f"answer_opt_{session_id[:8]}_{idx}"
            keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])

        # 添加自定义输入按钮
        keyboard.append([
            InlineKeyboardButton(
                "✏️ 自定义输入",
                callback_data=f"custom_input_{session_id[:8]}"
            )
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # 发送问题消息
        await update.effective_chat.send_message(
            message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        logger.info(f"发送 AskUserQuestion: {len(options)} 个选项")

    except Exception as e:
        logger.error(f"处理 AskUserQuestion 失败: {e}")
        # 恢复任务状态
        task.state = TaskState.RUNNING


def get_message_handlers():
    """返回消息处理器列表"""
    return [
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    ]
