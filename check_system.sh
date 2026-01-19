#!/bin/bash
#
# CloudWork System Check
# 系统环境检查脚本
#

set -e

echo "========================================"
echo "  CloudWork System Check"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 not found"
        return 1
    fi
}

check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python package: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Python package: $1 not found"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $1"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $1"
        return 0
    else
        echo -e "${YELLOW}!${NC} Directory missing: $1 (will be created)"
        return 1
    fi
}

errors=0

# 1. 系统信息
echo "1. System Information"
echo "   Python version: $(python3 --version)"
echo "   OS: $(uname -s)"
echo "   Kernel: $(uname -r)"
echo ""

# 2. 检查必需命令
echo "2. Required Commands"
check_command python3 || ((errors++))
check_command pip3 || ((errors++))
check_command claude || ((errors++))
check_command unbuffer || ((errors++))
echo ""

# 3. 检查 Python 依赖
echo "3. Python Dependencies"
check_python_package telegram || ((errors++))
check_python_package dotenv || ((errors++))
check_python_package pydantic || ((errors++))
check_python_package pydantic_settings || ((errors++))
check_python_package aiofiles || ((errors++))
echo ""

# 4. 检查项目文件
echo "4. Project Files"
check_file "src/bot/main.py" || ((errors++))
check_file "src/bot/services/session.py" || ((errors++))
check_file "src/bot/services/claude.py" || ((errors++))
check_file "src/bot/services/task.py" || ((errors++))
check_file "src/bot/handlers/commands.py" || ((errors++))
check_file "src/bot/handlers/messages.py" || ((errors++))
check_file "src/bot/handlers/callbacks.py" || ((errors++))
check_file "src/utils/config.py" || ((errors++))
check_file "config/.env" || ((errors++))
check_file "requirements.txt" || ((errors++))
echo ""

# 5. 检查目录
echo "5. Directories"
check_dir "data" || mkdir -p data
check_dir "logs" || mkdir -p logs
check_dir "workspace" || mkdir -p workspace
echo ""

# 6. 检查环境变量
echo "6. Environment Variables (from .env)"
if [ -f "config/.env" ]; then
    source config/.env

    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo -e "${GREEN}✓${NC} TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}..."
    else
        echo -e "${RED}✗${NC} TELEGRAM_BOT_TOKEN not set"
        ((errors++))
    fi

    if [ -n "$TELEGRAM_ALLOWED_USERS" ]; then
        echo -e "${GREEN}✓${NC} TELEGRAM_ALLOWED_USERS: $TELEGRAM_ALLOWED_USERS"
    else
        echo -e "${RED}✗${NC} TELEGRAM_ALLOWED_USERS not set"
        ((errors++))
    fi

    if [ -n "$ANTHROPIC_BASE_URL" ]; then
        echo -e "${GREEN}✓${NC} ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
    else
        echo -e "${YELLOW}!${NC} ANTHROPIC_BASE_URL not set (will use official API)"
    fi

    echo -e "${GREEN}✓${NC} DEFAULT_MODEL: ${DEFAULT_MODEL:-sonnet}"
    echo -e "${GREEN}✓${NC} DEFAULT_MODE: ${DEFAULT_MODE:-auto}"
else
    echo -e "${RED}✗${NC} config/.env not found"
    ((errors++))
fi
echo ""

# 7. 检查 Claude CLI
echo "7. Claude CLI Check"
if command -v claude &> /dev/null; then
    claude_version=$(claude --version 2>&1 | head -n 1 || echo "unknown")
    echo -e "${GREEN}✓${NC} Claude CLI version: $claude_version"

    # 测试 Claude CLI
    echo "   Testing Claude CLI..."
    if timeout 5 claude -p "test" --dangerously-skip-permissions 2>&1 | grep -q "Error\|error"; then
        echo -e "${YELLOW}!${NC} Claude CLI may have configuration issues"
    else
        echo -e "${GREEN}✓${NC} Claude CLI appears functional"
    fi
else
    echo -e "${RED}✗${NC} Claude CLI not installed"
    ((errors++))
fi
echo ""

# 8. 权限检查
echo "8. Permissions"
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}!${NC} Running as root (not recommended)"
    echo "   Please run as 'claude' user for proper Claude CLI access"
else
    echo -e "${GREEN}✓${NC} Running as user: $(whoami)"
fi
echo ""

# 9. 网络检查
echo "9. Network Check"
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Internet connectivity"
else
    echo -e "${RED}✗${NC} No internet connection"
    ((errors++))
fi

if [ -n "$ANTHROPIC_BASE_URL" ]; then
    echo "   Testing API endpoint..."
    if curl -s --max-time 5 "$ANTHROPIC_BASE_URL" &> /dev/null; then
        echo -e "${GREEN}✓${NC} API endpoint reachable: $ANTHROPIC_BASE_URL"
    else
        echo -e "${YELLOW}!${NC} API endpoint may be unreachable: $ANTHROPIC_BASE_URL"
    fi
fi
echo ""

# 10. 总结
echo "========================================"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Ready to run:"
    echo "  python3 -m src.bot.main"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $errors error(s) found${NC}"
    echo ""
    echo "Please fix the errors above before running."
    echo ""
    exit 1
fi
