"""
CloudWork Message Handlers

处理用户直接发送的文本消息（非命令）和图片消息
"""

import logging
import os
import re
import shlex
import uuid
from datetime import datetime
from typing import Optional, Tuple, List
from urllib.parse import urlparse, unquote

from telegram import Update, PhotoSize
from telegram.ext import ContextTypes, MessageHandler, filters

from ...utils.auth import is_authorized
from ...utils.config import settings
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
from ..services.whisper import whisper_service
from ..services.skills import transcribe_manager, TRANSCRIBE_TEMPLATES, resolve_audio_url, PLAUD_SHARE_PATTERN

logger = logging.getLogger(__name__)

# 支持的音频 MIME 类型前缀
AUDIO_MIME_PREFIXES = ("audio/", "video/ogg")
# 支持的音频文件扩展名
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".wma", ".opus", ".webm"}
# 音频 URL 正则：匹配以音频扩展名结尾的 HTTP(S) URL（忽略 query string）
AUDIO_URL_PATTERN = re.compile(
    r'https?://\S+\.(?:mp3|m4a|wav|ogg|flac|aac|wma|opus|webm)(?:\?\S*)?$',
    re.IGNORECASE
)
# 支持的音频分享平台 URL 模式（Plaud 等）
AUDIO_SHARE_PATTERNS = [
    re.compile(PLAUD_SHARE_PATTERN, re.IGNORECASE),
]

# 消息 ID 到会话 ID 的映射（用于回复消息时自动切换会话）
message_session_map: dict = {}

# 图片临时存储目录
IMAGES_DIR = os.path.join(settings.data_dir, "images")


async def download_telegram_photo(
    photo: PhotoSize,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
) -> Optional[str]:
    """
    下载 Telegram 图片到本地

    Args:
        photo: Telegram PhotoSize 对象
        context: Bot 上下文
        user_id: 用户 ID

    Returns:
        本地文件路径，失败返回 None
    """
    try:
        # 确保图片目录存在
        os.makedirs(IMAGES_DIR, exist_ok=True)

        # 生成唯一文件名
        file_ext = "jpg"  # Telegram 图片通常是 JPEG
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        local_path = os.path.join(IMAGES_DIR, filename)

        # 下载文件
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(local_path)

        logger.info(f"图片已下载: {local_path} ({photo.width}x{photo.height})")
        return local_path

    except Exception as e:
        logger.error(f"下载图片失败: {e}")
        return None


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户发送的图片消息

    下载图片到本地，然后让 Claude 通过 Read 工具读取图片
    """
    if not update.message or not update.message.photo:
        return

    user = update.effective_user
    if not user:
        return

    # 权限检查
    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 您没有使用权限")
        return

    user_id = user.id

    # 获取最大尺寸的图片
    photo = update.message.photo[-1]  # 最后一个是最大尺寸

    # 获取图片说明文字（caption）
    caption = update.message.caption or ""

    logger.info(f"收到图片: user={user_id}, size={photo.width}x{photo.height}, caption={caption[:50] if caption else '无'}")

    # 发送处理中消息
    status_message = await update.message.reply_text("🖼️ 正在下载图片...")

    # 下载图片
    local_path = await download_telegram_photo(photo, context, user_id)
    if not local_path:
        await status_message.edit_text("❌ 图片下载失败，请重试")
        return

    # 构建 prompt
    if caption:
        prompt = f"请查看这张图片并回答用户的问题。\n\n图片路径: {local_path}\n\n用户说明: {caption}"
    else:
        prompt = f"请查看这张图片并描述其内容。\n\n图片路径: {local_path}"

    # 将图片路径存入 context，以便清理
    if 'temp_images' not in context.user_data:
        context.user_data['temp_images'] = []
    context.user_data['temp_images'].append(local_path)

    # 使用 override_prompt 传递给 handle_message
    context.user_data['override_prompt'] = prompt

    # 删除状态消息，转交给 handle_message 处理
    try:
        await status_message.delete()
    except Exception:
        pass

    # 调用文本消息处理器
    await handle_message(update, context)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户发送的语音消息

    下载语音 → Whisper 转录 → 展示模版选择按钮
    """
    if not update.message or not update.message.voice:
        return

    user = update.effective_user
    if not user:
        return

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 您没有使用权限")
        return

    if not whisper_service.is_configured:
        await update.message.reply_text("❌ 语音转文字未配置，请设置 WHISPER_API_KEY")
        return

    voice = update.message.voice
    duration = voice.duration or 0
    logger.info(f"收到语音: user={user.id}, duration={duration}s")

    status_message = await update.message.reply_text("🎤 正在转录语音...")

    try:
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = bytes(await file.download_as_bytearray())

        await _transcribe_and_show_templates(
            update, context, audio_bytes, "voice.ogg", status_message
        )

    except Exception as e:
        logger.error(f"语音处理失败: {e}")
        await status_message.edit_text(f"❌ 语音处理失败: {str(e)[:100]}")


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户发送的音频消息 (Telegram Audio 类型)

    下载音频 → Whisper 转录 → 展示模版选择按钮
    """
    if not update.message or not update.message.audio:
        return

    user = update.effective_user
    if not user:
        return

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 您没有使用权限")
        return

    if not whisper_service.is_configured:
        await update.message.reply_text("❌ 语音转文字未配置，请设置 WHISPER_API_KEY")
        return

    audio = update.message.audio
    file_name = audio.file_name or "audio.mp3"
    file_size = audio.file_size or 0
    duration = audio.duration or 0

    logger.info(f"收到音频: user={user.id}, file={file_name}, size={file_size}, duration={duration}s")

    # 检查文件大小 (Whisper API 限制 25MB)
    if file_size > 25 * 1024 * 1024:
        await update.message.reply_text("❌ 音频文件过大（超过 25MB），请压缩后重试")
        return

    status_message = await update.message.reply_text(f"🎵 正在转录音频 ({file_name})...")

    try:
        file = await context.bot.get_file(audio.file_id)
        audio_bytes = bytes(await file.download_as_bytearray())

        await _transcribe_and_show_templates(
            update, context, audio_bytes, file_name, status_message
        )

    except Exception as e:
        logger.error(f"音频处理失败: {e}")
        await status_message.edit_text(f"❌ 音频处理失败: {str(e)[:100]}")


async def handle_audio_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户以文件形式发送的音频 (Document 类型)

    检查 MIME 类型或扩展名 → 下载 → Whisper 转录 → 展示模版选择按钮
    """
    if not update.message or not update.message.document:
        return

    user = update.effective_user
    if not user:
        return

    document = update.message.document
    mime_type = document.mime_type or ""
    file_name = document.file_name or ""
    file_ext = os.path.splitext(file_name)[1].lower() if file_name else ""

    # 检查是否为音频文件
    is_audio = (
        any(mime_type.startswith(prefix) for prefix in AUDIO_MIME_PREFIXES)
        or file_ext in AUDIO_EXTENSIONS
    )

    if not is_audio:
        return  # 不是音频文件，跳过（让其他 handler 处理）

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ 您没有使用权限")
        return

    if not whisper_service.is_configured:
        await update.message.reply_text("❌ 语音转文字未配置，请设置 WHISPER_API_KEY")
        return

    file_size = document.file_size or 0

    logger.info(f"收到音频文件: user={user.id}, file={file_name}, mime={mime_type}, size={file_size}")

    # 检查文件大小
    if file_size > 25 * 1024 * 1024:
        await update.message.reply_text("❌ 音频文件过大（超过 25MB），请压缩后重试")
        return

    status_message = await update.message.reply_text(f"🎵 正在转录音频文件 ({file_name})...")

    try:
        file = await context.bot.get_file(document.file_id)
        audio_bytes = bytes(await file.download_as_bytearray())

        await _transcribe_and_show_templates(
            update, context, audio_bytes, file_name or "audio.ogg", status_message
        )

    except Exception as e:
        logger.error(f"音频文件处理失败: {e}")
        await status_message.edit_text(f"❌ 音频文件处理失败: {str(e)[:100]}")


TRANSCRIPTS_DIR = os.path.join(settings.data_dir, "transcripts")


def _save_transcription(source_filename: str, text: str, template_name: Optional[str] = None) -> Optional[str]:
    """
    保存转录/加工结果到 md 文件

    文件命名：{date}_{source}[_{template}].md
    存储目录：data/transcripts/

    Args:
        source_filename: 原始音频文件名
        text: 转录或加工后的文本
        template_name: 模版名称（如 "会议纪要"），None 表示原始转录

    Returns:
        保存的文件路径，失败返回 None
    """
    try:
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

        # 构建文件名
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_name = os.path.splitext(source_filename)[0]
        # 清理文件名中的特殊字符
        source_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', source_name)[:30]

        if template_name:
            md_filename = f"{date_str}_{source_name}_{template_name}.md"
        else:
            md_filename = f"{date_str}_{source_name}_转录原文.md"

        filepath = os.path.join(TRANSCRIPTS_DIR, md_filename)

        # 写入 md 文件
        header = f"# {template_name or '转录原文'}\n\n"
        header += f"- 来源: {source_filename}\n"
        header += f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"- 字数: {len(text)}\n\n---\n\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + text)

        return filepath

    except Exception as e:
        logger.error(f"保存转录文件失败: {e}")
        return None


async def _transcribe_and_show_templates(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    audio_bytes: bytes,
    filename: str,
    status_message
):
    """
    公共方法：转录音频并展示模版选择按钮

    Args:
        update: Telegram Update
        context: Bot 上下文
        audio_bytes: 音频字节数据
        filename: 文件名（含扩展名）
        status_message: 已发送的状态消息（用于编辑）
    """
    user = update.effective_user
    user_id = user.id

    # 调用 Whisper 转录
    text = whisper_service.transcribe(audio_bytes, filename=filename)

    if not text:
        await status_message.edit_text("❌ 音频转录失败，请重试或直接输入文字")
        return

    logger.info(f"转录完成: user={user_id}, {len(audio_bytes)} bytes -> {len(text)} chars")

    # 保存转录原文到 md 文件
    saved_path = _save_transcription(filename, text)
    if saved_path:
        logger.info(f"转录已保存: {saved_path}")

    # 暂存转录文本和保存路径
    context.user_data['pending_transcription'] = text
    context.user_data['transcription_path'] = saved_path

    # 构建预览（前 200 字）
    preview = text[:200]
    if len(text) > 200:
        preview += "..."

    # 展示转录结果和模版选择按钮
    template_keyboard = transcribe_manager.get_template_keyboard(user_id)

    saved_info = f"\n💾 已保存: `{os.path.basename(saved_path)}`" if saved_path else ""

    await status_message.edit_text(
        f"✅ 转录完成 ({len(text)} 字){saved_info}\n\n"
        f"📜 {preview}\n\n"
        f"请选择整理方式：",
        reply_markup=template_keyboard
    )


async def handle_audio_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """
    处理用户发送的音频 URL 链接

    支持直接音频 URL 和平台分享链接（如 Plaud）。
    流程：解析 URL → 下载音频 → Whisper 转录 → 展示模版选择按钮
    """
    import httpx

    if not whisper_service.is_configured:
        await update.message.reply_text("❌ 语音转文字未配置，请设置 WHISPER_API_KEY")
        return

    logger.info(f"收到音频 URL: user={update.effective_user.id}, url={url[:80]}")

    status_message = await update.message.reply_text("🔗 正在解析音频链接...")

    try:
        # 解析 URL（支持 Plaud 分享链接等平台）
        audio_url, filename = await resolve_audio_url(url)
        if not audio_url:
            await status_message.edit_text("❌ 无法解析音频链接，请检查 URL 是否正确")
            return

        await status_message.edit_text(f"🔗 正在下载音频 ({filename})...")

        # 下载音频
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()

            if len(resp.content) > 25 * 1024 * 1024:
                await status_message.edit_text("❌ 音频文件过大（超过 25MB），请压缩后重试")
                return

            audio_bytes = resp.content

        await status_message.edit_text(f"🎤 正在转录音频 ({filename})...")

        await _transcribe_and_show_templates(
            update, context, audio_bytes, filename, status_message
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"下载音频失败 (HTTP {e.response.status_code}): {url}")
        await status_message.edit_text(f"❌ 下载失败 (HTTP {e.response.status_code})")
    except Exception as e:
        logger.error(f"音频 URL 处理失败: {e}")
        await status_message.edit_text(f"❌ 音频处理失败: {str(e)[:100]}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理用户直接发送的文本消息

    支持:
    - 在当前活跃会话中对话
    - 回复历史消息自动切换到该会话
    - 自动创建新会话（如果没有活跃会话）
    - 通过 override_prompt 接收图片消息
    - 发送音频 URL 自动转录
    """
    # 检查是否有 override_prompt（从图片处理器或技能命令传入）
    override_prompt = context.user_data.pop('override_prompt', None)

    # 如果没有 override_prompt，需要有文本消息
    if not override_prompt and (not update.message or not update.message.text):
        return

    user = update.effective_user
    if not user:
        return

    # 兼容 callback query update（从转录模版回调等场景传入）
    # callback query 的 update.message 为 None，使用 callback_query.message 替代
    msg = update.message
    if msg is None and update.callback_query:
        msg = update.callback_query.message
    if msg is None:
        return

    # 权限检查（override_prompt 场景已在调用方检查过）
    if not override_prompt and not is_authorized(user.id):
        await msg.reply_text("⛔ 您没有使用权限")
        return

    user_id = user.id
    chat_id = update.effective_chat.id

    # 确定 prompt
    prompt = override_prompt if override_prompt else update.message.text.strip()

    if not prompt:
        return

    # 检查是否为音频 URL 或分享链接（仅对用户直接输入的文本检测，不对 override_prompt 检测）
    if not override_prompt:
        stripped = prompt.strip()
        is_audio_url = AUDIO_URL_PATTERN.match(stripped)
        is_share_url = any(p.match(stripped) for p in AUDIO_SHARE_PATTERNS)
        if is_audio_url or is_share_url:
            await handle_audio_url(update, context, stripped)
            return

    # 检查是否有待处理的技能命令
    pending_skill = context.user_data.get('pending_skill')
    if pending_skill:
        # 清除待处理状态
        del context.user_data['pending_skill']
        logger.info(f"技能快捷输入: {pending_skill} -> {prompt[:50]}...")

        # 转录自定义提示：用户输入的文本作为自定义 prompt 加工转录文本
        if pending_skill == 'transcribe_custom':
            transcribed_text = context.user_data.pop('pending_transcription', None)
            if not transcribed_text:
                await msg.reply_text("❌ 转录文本已过期，请重新发送音频")
                return
            # 构建自定义加工 prompt
            custom_prompt = f"{prompt}\n\n以下是需要处理的转录文本：\n{transcribed_text}"
            context.user_data['override_prompt'] = custom_prompt
            await handle_message(update, context)
            return

        # 转发到命令处理器
        from .commands import plan_command, ralph_command
        # 使用 shlex.split 正确解析参数（保留引号内的空格）
        try:
            context.args = shlex.split(prompt)
        except ValueError:
            # 如果 shlex 解析失败（如引号不匹配），fallback 到简单空格分割
            context.args = prompt.split()
        if pending_skill == 'plan':
            await plan_command(update, context)
        elif pending_skill == 'ralph':
            await ralph_command(update, context)
        return

    logger.info(f"收到消息: user={user_id}, text={prompt[:50]}...")

    # 检查是否回复了某条消息（自动切换会话并获取引用内容）
    session_id, quoted_content = await _handle_reply_session_switch(update, user_id)

    # 如果有被引用的 bot 消息内容，添加到 prompt 中作为上下文
    if quoted_content:
        # 构建带引用上下文的 prompt
        prompt = f"[引用的上下文]\n{quoted_content}\n\n[用户的问题]\n{prompt}"
        logger.info(f"添加引用上下文: {len(quoted_content)} 字符")

    # 如果没有通过回复切换，使用当前活跃会话
    if not session_id:
        session_id = session_manager.get_active_session_id(user_id)

    # 检查是否有运行中的任务（仅检查当前会话，允许在不同会话中并行执行）
    # 如果 session_id 是 None，说明要创建新会话，不阻止
    if session_id and task_manager.has_running_task(user_id, session_id):
        # 检查是否在等待用户输入
        if task_manager.is_waiting_input(user_id, session_id):
            # 设置用户回复
            task_manager.set_user_reply(user_id, session_id, prompt)
            await msg.reply_text("✅ 已收到您的回复，继续执行...")
            return
        else:
            await msg.reply_text(
                "⏳ 当前会话有任务正在执行中\n\n"
                "• 点击「取消任务」按钮打断\n"
                "• 或切换项目/会话后发送新任务"
            )
            return

    # 发送初始状态消息（带取消按钮）
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    cancel_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏹️ 取消任务", callback_data=f"cancel_task_{user_id}")]
    ])
    status_message = await msg.reply_text(
        "🚀 正在启动 Claude...",
        reply_markup=cancel_button
    )

    # 如果没有活跃会话，创建新会话
    if not session_id:
        session_name = generate_session_name(prompt)
        pending_session_id = session_manager.generate_pending_session_id(user_id)
        session = session_manager.create_session(user_id, pending_session_id, name=session_name)
        session_id = session.id
        logger.info(f"自动创建新会话: {session_id[:8]}...")

    # 记录消息到会话的映射
    message_session_map[status_message.message_id] = session_id

    # 定义进度回调（保持取消按钮）
    async def progress_callback(text: str, status: Optional[str]):
        """更新进度消息，保持取消按钮"""
        try:
            progress_text = format_progress_text(text, status=status)
            await safe_edit_message(
                status_message,
                progress_text,
                parse_mode=None,
                reply_markup=cancel_button  # 保持取消按钮
            )
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

        # 如果是转录模版加工，保存加工结果到 md
        pending_save = context.user_data.pop('pending_save_template', None)
        if pending_save and output:
            saved = _save_transcription(
                pending_save['source_filename'],
                output,
                template_name=pending_save['template_name']
            )
            if saved:
                logger.info(f"模版加工结果已保存: {saved}")

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
) -> Tuple[Optional[str], Optional[str]]:
    """
    处理回复消息时的会话切换和上下文引用

    如果用户回复了某条历史消息：
    1. 自动切换到该消息所属的会话
    2. 获取被回复的消息内容作为上下文

    Returns:
        (session_id, quoted_content) - 会话 ID 和被引用的消息内容
    """
    if not update.message or not update.message.reply_to_message:
        return None, None

    reply_msg = update.message.reply_to_message
    reply_msg_id = reply_msg.message_id

    # 获取被回复的消息内容（仅获取 bot 发送的消息内容）
    quoted_content = None
    if reply_msg.from_user and reply_msg.from_user.is_bot:
        # 这是 bot 发送的消息，提取内容作为上下文
        if reply_msg.text:
            quoted_content = reply_msg.text
        elif reply_msg.caption:
            quoted_content = reply_msg.caption

    # 从映射中查找会话 ID
    session_id = None
    if reply_msg_id in message_session_map:
        session_id = message_session_map[reply_msg_id]
        # 切换到该会话
        session_manager.set_active_session(user_id, session_id)
        logger.info(f"通过回复消息切换会话: {session_id[:8]}...")

    return session_id, quoted_content


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
        # 文本消息处理器
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        ),
        # 图片消息处理器
        MessageHandler(
            filters.PHOTO,
            handle_photo_message
        ),
        # 语音消息处理器
        MessageHandler(
            filters.VOICE,
            handle_voice_message
        ),
        # 音频消息处理器 (Telegram Audio 类型)
        MessageHandler(
            filters.AUDIO,
            handle_audio_message
        ),
        # 音频文件处理器 (Document 类型，内部检查 MIME)
        MessageHandler(
            filters.Document.ALL,
            handle_audio_document
        ),
    ]
