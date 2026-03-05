"""
Whisper 语音转文字服务

通过 OpenAI 兼容 API（默认 Groq）将语音消息转为文本。
"""

import io
import logging
from typing import Optional

from openai import OpenAI

from ...utils.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """语音转文字服务"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Optional[OpenAI]:
        """懒加载 OpenAI 客户端"""
        if self._client is None and settings.whisper_api_key:
            self._client = OpenAI(
                api_key=settings.whisper_api_key,
                base_url=settings.whisper_base_url,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(settings.whisper_api_key)

    def transcribe(self, audio_data: bytes, filename: str = "voice.ogg") -> Optional[str]:
        """
        将音频数据转为文本

        Args:
            audio_data: 音频文件的字节数据
            filename: 文件名（含扩展名，用于 API 识别格式）

        Returns:
            转写文本，失败返回 None
        """
        if not self.client:
            logger.error("Whisper 未配置，请设置 WHISPER_API_KEY")
            return None

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename

            transcription = self.client.audio.transcriptions.create(
                model=settings.whisper_model,
                file=audio_file,
            )

            text = transcription.text.strip()
            logger.info(f"语音转写完成: {len(audio_data)} bytes -> {len(text)} chars")
            return text if text else None

        except Exception as e:
            logger.error(f"语音转写失败: {e}")
            return None


# 全局实例
whisper_service = WhisperService()
