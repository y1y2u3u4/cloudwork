"""
CloudWork Output Formatting Utilities

处理 Claude 输出的格式化、Markdown 转换、安全编辑等
"""

import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

# Telegram 消息长度限制
MAX_MESSAGE_LENGTH = 4096

# ANSI 转义码正则
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi_codes(text: str) -> str:
    """移除 ANSI 转义码"""
    if not text:
        return ""
    return ANSI_ESCAPE_PATTERN.sub('', text)


def escape_markdown(text: str) -> str:
    """
    转义 Telegram Markdown V1 特殊字符

    需要转义: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return ""

    # Markdown V1 特殊字符
    special_chars = ['_', '*', '[', ']', '(', ')', '`', '\\']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def escape_markdown_v2(text: str) -> str:
    """
    转义 Telegram MarkdownV2 特殊字符
    """
    if not text:
        return ""

    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#',
        '+', '-', '=', '|', '{', '}', '.', '!'
    ]

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def convert_markdown_for_telegram(text: str) -> Tuple[str, str]:
    """
    转换 Markdown 为 Telegram 兼容格式

    Returns:
        (converted_text, parse_mode)
    """
    if not text:
        return "", None

    # 清理 ANSI 码
    text = strip_ansi_codes(text)

    # 简化处理：如果文本包含太多复杂 Markdown，使用纯文本
    code_block_count = text.count('```')
    if code_block_count > 6 or len(text) > 3000:
        # 复杂内容使用纯文本
        return text, None

    try:
        # 尝试简单的 Markdown 转换
        # 保留代码块
        converted = text

        # 处理标题（## Title -> *Title*）
        converted = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', converted, flags=re.MULTILINE)

        # 如果转换后太长，截断
        if len(converted) > MAX_MESSAGE_LENGTH:
            converted = converted[:MAX_MESSAGE_LENGTH - 50] + "\n\n...(内容过长，已截断)"

        return converted, 'Markdown'

    except Exception as e:
        logger.warning(f"Markdown 转换失败: {e}")
        return text, None


def convert_to_telegram_markdown(text: str) -> str:
    """
    将标准 Markdown 转换为 Telegram 兼容格式

    Telegram Markdown V1 支持:
    - *bold*
    - _italic_
    - `code`
    - ```code block```
    - [text](url)

    不支持: 标题(##)、列表(-/*)、表格、引用(>)
    """
    if not text:
        return ""

    lines = text.split('\n')
    result_lines = []
    in_code_block = False

    for line in lines:
        # 检测代码块
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue

        # 代码块内不做转换
        if in_code_block:
            result_lines.append(line)
            continue

        # 转换标题为粗体
        # ## Title -> *Title*
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            title = header_match.group(2).strip()
            # 移除标题中可能的 * 避免冲突
            title = title.replace('*', '')
            result_lines.append(f'*{title}*')
            continue

        # 转换列表项：- item -> • item
        list_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
        if list_match:
            indent = list_match.group(1)
            content = list_match.group(2)
            result_lines.append(f'{indent}• {content}')
            continue

        # 转换数字列表：1. item -> 1) item
        num_list_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
        if num_list_match:
            indent = num_list_match.group(1)
            num = num_list_match.group(2)
            content = num_list_match.group(3)
            result_lines.append(f'{indent}{num}) {content}')
            continue

        # 移除引用符号
        if line.strip().startswith('>'):
            line = line.replace('>', '│', 1)

        # 移除水平线
        if re.match(r'^[-*_]{3,}$', line.strip()):
            result_lines.append('─' * 20)
            continue

        result_lines.append(line)

    return '\n'.join(result_lines)


def format_claude_output(text: str, max_length: int = 3800) -> Tuple[str, Optional[str]]:
    """
    格式化 Claude 输出用于 Telegram 显示

    将 Claude 的 Markdown 输出转换为 Telegram 兼容格式

    Returns:
        (formatted_text, parse_mode)
    """
    if not text:
        return "无输出", None

    # 清理 ANSI
    text = strip_ansi_codes(text)

    # 转换为 Telegram 兼容的 Markdown
    converted = convert_to_telegram_markdown(text)

    # 尝试使用 Markdown
    try:
        # 检查是否有未闭合的特殊字符（可能导致解析错误）
        # 统计代码块外的特殊字符
        temp = converted
        # 移除代码块内容后检查
        temp = re.sub(r'```[\s\S]*?```', '', temp)
        temp = re.sub(r'`[^`]+`', '', temp)

        # 检查未配对的 * 和 _
        asterisk_count = temp.count('*')
        underscore_count = temp.count('_')

        # 如果特殊字符是奇数，可能导致解析问题
        if asterisk_count % 2 != 0 or underscore_count % 2 != 0:
            # 移除可能导致问题的字符
            converted = converted.replace('*', '').replace('_', '')
            return converted, None

        return converted, 'Markdown'

    except Exception as e:
        logger.warning(f"Markdown 格式化失败: {e}")
        # 回退到纯文本
        plain = converted.replace('*', '').replace('_', '').replace('`', '')
        return plain, None


def safe_truncate(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """安全截断文本"""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    # 在合适的位置截断
    truncated = text[:max_length - 50]

    # 尝试在换行处截断
    last_newline = truncated.rfind('\n')
    if last_newline > max_length - 200:
        truncated = truncated[:last_newline]

    return truncated + "\n\n...(已截断)"


def split_long_message(text: str, max_length: int = 3800) -> List[str]:
    """
    智能分段长消息

    在自然边界（段落、代码块、列表项）处分割，保持格式完整性

    Args:
        text: 待分割的文本
        max_length: 每段最大长度（预留空间给分页标记）

    Returns:
        分段后的文本列表
    """
    if not text:
        return ["无输出"]

    # 清理 ANSI
    text = strip_ansi_codes(text)

    # 先转换为 Telegram 兼容格式
    text = convert_to_telegram_markdown(text)

    # 如果不需要分段，直接返回
    if len(text) <= max_length:
        return [text]

    segments = []
    current_segment = ""
    in_code_block = False
    code_block_lang = ""

    # 按行处理，保持格式
    lines = text.split('\n')

    for line in lines:
        # 检测代码块开始/结束
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lang = line.strip()[3:]  # 获取语言标记
            else:
                in_code_block = False

        # 计算添加这行后的长度
        potential_length = len(current_segment) + len(line) + 1  # +1 for \n

        # 如果添加这行会超出限制
        if potential_length > max_length:
            # 如果当前段不为空，保存它
            if current_segment.strip():
                # 如果在代码块内，需要关闭它
                if in_code_block:
                    current_segment += "\n```"
                segments.append(current_segment.strip())

            # 开始新段
            # 如果在代码块内，需要重新开始代码块
            if in_code_block:
                current_segment = f"```{code_block_lang}\n{line}"
            else:
                current_segment = line
        else:
            # 正常添加行
            if current_segment:
                current_segment += "\n" + line
            else:
                current_segment = line

    # 添加最后一段
    if current_segment.strip():
        segments.append(current_segment.strip())

    # 如果没有成功分段（极端情况），强制分割
    if not segments:
        # 强制按长度分割
        for i in range(0, len(text), max_length - 100):
            chunk = text[i:i + max_length - 100]
            segments.append(chunk)

    # 添加分页标记
    total = len(segments)
    if total > 1:
        for i, segment in enumerate(segments):
            page_marker = f"\n\n📄 [{i + 1}/{total}]"
            segments[i] = segment + page_marker

    return segments


def format_progress_text(
    accumulated_text: str,
    current_tool: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    格式化进度文本（纯文本模式）

    用于实时显示执行进度，避免 Markdown 解析问题
    """
    # 构建状态文本
    if status:
        progress_text = status[:400]
    elif current_tool:
        progress_text = f"🔧 正在执行: {current_tool}"
    else:
        progress_text = "⏳ 执行中..."

    # 显示部分输出预览
    if accumulated_text:
        cleaned_text = strip_ansi_codes(accumulated_text)
        # 只显示最后 150 个字符
        preview = cleaned_text[-150:] if len(cleaned_text) > 150 else cleaned_text
        # 移除可能导致问题的字符
        safe_preview = preview.replace('`', "'").replace('*', '').replace('_', '')
        safe_preview = safe_preview.replace('[', '').replace(']', '').replace('\\', '')

        if safe_preview.strip():
            progress_text += f"\n\n预览：\n{safe_preview}"

    # 严格限制长度
    MAX_PROGRESS_LENGTH = 1000
    if len(progress_text) > MAX_PROGRESS_LENGTH:
        progress_text = progress_text[:MAX_PROGRESS_LENGTH - 30] + "\n...(输出过长)"

    return progress_text


def format_session_info(session: dict, is_active: bool = False) -> str:
    """格式化会话信息"""
    name = session.get("name", "未命名")
    message_count = session.get("message_count", 0)
    last_active = session.get("last_active", "")

    # 解析最后活跃时间
    if last_active:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(last_active)
            time_str = dt.strftime("%m-%d %H:%M")
        except Exception:
            time_str = last_active[:16]
    else:
        time_str = "未知"

    active_marker = "▶️ " if is_active else ""
    return f"{active_marker}{name} ({message_count}条) - {time_str}"


def format_error_message(error: str) -> str:
    """格式化错误消息"""
    # 转义特殊字符
    safe_error = escape_markdown(str(error))
    # 限制长度
    if len(safe_error) > 500:
        safe_error = safe_error[:500] + "..."
    return f"❌ *错误*\n\n`{safe_error}`"


def generate_session_name(prompt: str) -> str:
    """
    根据提示词生成会话名称

    简单实现：提取关键词或前几个字
    """
    if not prompt:
        return "新会话"

    # 清理空白
    clean_prompt = prompt.strip()

    # 移除常见前缀
    prefixes_to_remove = ['帮我', '请', '我想', '能不能', '可以', 'please', 'can you']
    for prefix in prefixes_to_remove:
        if clean_prompt.lower().startswith(prefix):
            clean_prompt = clean_prompt[len(prefix):].strip()

    # 截取合适长度
    if len(clean_prompt) > 20:
        # 尝试在标点处截断
        for punct in ['，', ',', '。', '.', '？', '?', '！', '!', '：', ':']:
            pos = clean_prompt.find(punct)
            if 5 < pos < 25:
                clean_prompt = clean_prompt[:pos]
                break
        else:
            clean_prompt = clean_prompt[:20]

    return clean_prompt or "新会话"


async def safe_edit_message(
    message,
    text: str,
    parse_mode: Optional[str] = 'Markdown',
    reply_markup=None
):
    """
    安全地编辑消息，处理各种错误情况

    自动处理：
    - 消息未修改
    - Markdown 解析错误（回退到纯文本）
    - 消息过长
    """
    try:
        await message.edit_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except Exception as e:
        error_str = str(e)

        # 消息未修改，忽略
        if "Message is not modified" in error_str:
            return

        # Markdown 解析错误，回退到纯文本
        if any(keyword in error_str for keyword in ['parse', 'entities', 'Can\'t parse']):
            logger.warning(f"Markdown 解析错误，回退到纯文本: {e}")
            try:
                # 移除所有可能的 Markdown 标记
                plain_text = text.replace('*', '').replace('_', '').replace('`', '')
                await message.edit_text(
                    plain_text,
                    parse_mode=None,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"纯文本编辑也失败: {e2}")

        # 消息过长
        elif "Message is too long" in error_str:
            logger.warning("消息过长，截断后重试")
            try:
                truncated = safe_truncate(text, MAX_MESSAGE_LENGTH - 100)
                await message.edit_text(
                    truncated,
                    parse_mode=None,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"截断后编辑也失败: {e2}")

        else:
            logger.error(f"编辑消息失败: {e}")
