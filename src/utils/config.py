"""
CloudWork Configuration Management

使用 pydantic-settings 进行配置管理，支持环境变量和 .env 文件。
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """CloudWork 配置类"""

    # =====================================
    # Telegram Bot
    # =====================================
    telegram_bot_token: str = ""  # Required at runtime, but allow empty for import
    telegram_allowed_users: List[int] = []

    @field_validator('telegram_allowed_users', mode='before')
    @classmethod
    def parse_allowed_users(cls, v):
        """解析逗号分隔的用户 ID 列表或单个整数"""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(uid.strip()) for uid in v.split(',') if uid.strip()]
        if isinstance(v, int):
            # 单个整数，转换为列表
            return [v]
        if isinstance(v, list):
            return v
        return []

    # =====================================
    # Claude API
    # =====================================
    anthropic_api_key: str = ""
    anthropic_base_url: Optional[str] = None
    anthropic_auth_token: Optional[str] = None

    # =====================================
    # Claude Settings
    # =====================================
    default_model: str = "sonnet"
    default_mode: str = "auto"
    command_timeout: int = 300
    claude_binary: str = "claude"  # 本地 Mac 可设为完整路径

    # =====================================
    # Storage
    # =====================================
    work_dir: str = "./"
    data_dir: str = "./data"
    workspace_dir: str = "./workspace"

    # =====================================
    # Session Settings
    # =====================================
    auto_archive_minutes: int = 30
    max_concurrent_tasks: int = 5

    # =====================================
    # Logging
    # =====================================
    log_level: str = "INFO"
    log_file: str = "./logs/cloudwork.log"

    class Config:
        """Pydantic 配置"""
        env_file = "config/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的环境变量

    def get_claude_env(self) -> dict:
        """获取 Claude CLI 需要的环境变量"""
        env = os.environ.copy()

        # 如果配置了 Auth Token，强制移除可能存在的 API Key
        # 防止 Claude CLI 优先使用 API Key 导致认证模式错误
        if self.anthropic_auth_token:
            if "ANTHROPIC_API_KEY" in env:
                del env["ANTHROPIC_API_KEY"]

        if self.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = self.anthropic_api_key

        if self.anthropic_base_url:
            env["ANTHROPIC_BASE_URL"] = self.anthropic_base_url

        if self.anthropic_auth_token:
            env["ANTHROPIC_AUTH_TOKEN"] = self.anthropic_auth_token

        return env

    def validate_config(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []

        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        if not self.telegram_allowed_users:
            errors.append("TELEGRAM_ALLOWED_USERS is required")

        if not self.anthropic_api_key and not self.anthropic_base_url:
            errors.append("Either ANTHROPIC_API_KEY or ANTHROPIC_BASE_URL is required")

        return errors


def load_settings() -> Settings:
    """加载配置"""
    # 尝试多个可能的 .env 文件位置
    env_paths = [
        "config/.env",
        ".env",
        "../config/.env",
    ]

    for path in env_paths:
        if os.path.exists(path):
            os.environ.setdefault("ENV_FILE", path)
            break

    return Settings()


# 全局配置实例
settings = load_settings()
