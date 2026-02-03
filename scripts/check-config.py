#!/usr/bin/env python3
"""
CloudWork 配置验证脚本
验证 config/.env 配置是否正确
"""

import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_config():
    """验证配置文件"""
    print("🔍 检查 CloudWork 配置...\n")

    errors = []
    warnings = []

    # 检查 .env 文件是否存在
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
    if not os.path.exists(env_path):
        print("❌ config/.env 文件不存在")
        print("   请运行: cp config/.env.example config/.env")
        return False

    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv(env_path)

    # 必需配置检查
    print("📋 必需配置:")

    # Telegram Bot Token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token or bot_token == "your_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN 未设置")
        print("   ❌ TELEGRAM_BOT_TOKEN: 未设置")
    else:
        # 简单验证格式
        if ":" in bot_token and len(bot_token) > 30:
            print(f"   ✅ TELEGRAM_BOT_TOKEN: {bot_token[:10]}...{bot_token[-5:]}")
        else:
            errors.append("TELEGRAM_BOT_TOKEN 格式可能不正确")
            print(f"   ⚠️  TELEGRAM_BOT_TOKEN: 格式可能不正确")

    # Telegram 授权用户
    allowed_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    if not allowed_users or allowed_users == "123456789,987654321":
        errors.append("TELEGRAM_ALLOWED_USERS 未设置")
        print("   ❌ TELEGRAM_ALLOWED_USERS: 未设置")
    else:
        user_list = [u.strip() for u in allowed_users.split(",") if u.strip()]
        if all(u.isdigit() for u in user_list):
            print(f"   ✅ TELEGRAM_ALLOWED_USERS: {len(user_list)} 个用户")
        else:
            warnings.append("TELEGRAM_ALLOWED_USERS 包含非数字字符")
            print(f"   ⚠️  TELEGRAM_ALLOWED_USERS: 格式可能不正确")

    # Claude API 配置
    print("\n📋 Claude API 配置:")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "")

    if api_key and api_key != "sk-ant-xxxxx":
        if api_key.startswith("sk-ant-"):
            print(f"   ✅ ANTHROPIC_API_KEY: {api_key[:12]}...{api_key[-4:]}")
        else:
            warnings.append("ANTHROPIC_API_KEY 格式可能不正确")
            print(f"   ⚠️  ANTHROPIC_API_KEY: 格式可能不正确")
    elif base_url:
        print(f"   ✅ ANTHROPIC_BASE_URL: {base_url}")
        if auth_token:
            print(f"   ✅ ANTHROPIC_AUTH_TOKEN: {auth_token[:8]}...")
        else:
            warnings.append("使用自定义 API 但未设置 ANTHROPIC_AUTH_TOKEN")
            print("   ⚠️  ANTHROPIC_AUTH_TOKEN: 未设置")
    else:
        errors.append("Claude API 未配置 (需要 ANTHROPIC_API_KEY 或 ANTHROPIC_BASE_URL)")
        print("   ❌ Claude API: 未配置")

    # 可选配置检查
    print("\n📋 可选配置:")

    model = os.getenv("DEFAULT_MODEL", "sonnet")
    print(f"   ℹ️  DEFAULT_MODEL: {model}")

    mode = os.getenv("DEFAULT_MODE", "auto")
    print(f"   ℹ️  DEFAULT_MODE: {mode}")

    timeout = os.getenv("COMMAND_TIMEOUT", "300")
    print(f"   ℹ️  COMMAND_TIMEOUT: {timeout}s")

    # 本地节点配置
    local_url = os.getenv("LOCAL_NODE_URL", "")
    if local_url:
        print(f"\n📋 本地节点配置:")
        print(f"   ℹ️  LOCAL_NODE_URL: {local_url}")
        local_token = os.getenv("LOCAL_API_TOKEN", "")
        if local_token:
            print(f"   ✅ LOCAL_API_TOKEN: {local_token[:8]}...")
        else:
            warnings.append("LOCAL_NODE_URL 已设置但 LOCAL_API_TOKEN 未设置")
            print("   ⚠️  LOCAL_API_TOKEN: 未设置")

    # 检查 Claude CLI
    print("\n📋 依赖检查:")
    import shutil
    claude_path = shutil.which("claude")
    if claude_path:
        print(f"   ✅ Claude CLI: {claude_path}")
    else:
        warnings.append("Claude CLI 未安装或不在 PATH 中")
        print("   ⚠️  Claude CLI: 未找到 (npm install -g @anthropic-ai/claude-code)")

    # 检查目录
    print("\n📋 目录检查:")
    dirs_to_check = [
        ("data", "会话数据"),
        ("workspace", "项目工作空间"),
        ("logs", "日志目录"),
    ]

    project_root = os.path.dirname(os.path.dirname(__file__))
    for dir_name, desc in dirs_to_check:
        dir_path = os.path.join(project_root, dir_name)
        if os.path.isdir(dir_path):
            print(f"   ✅ {dir_name}/: {desc}")
        else:
            print(f"   ⚠️  {dir_name}/: 不存在 (将自动创建)")

    # 结果汇总
    print("\n" + "=" * 50)

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:")
        for e in errors:
            print(f"   • {e}")
        print("\n请修复以上错误后再启动 Bot。")
        return False

    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:")
        for w in warnings:
            print(f"   • {w}")

    print("\n✅ 配置验证通过！")
    print("\n启动 Bot:")
    print("   python -m src.bot.main")

    return True


if __name__ == "__main__":
    try:
        success = check_config()
        sys.exit(0 if success else 1)
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("   请运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        sys.exit(1)
