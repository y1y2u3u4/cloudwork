# Installation Guide

CloudWork 安装指南，支持 Docker、VPS 和手动安装三种方式。

## Prerequisites

### 系统要求

- **操作系统**: Ubuntu 20.04+, Debian 11+, macOS, 或任何支持 Docker 的系统
- **Python**: 3.9+ (推荐 3.11)
- **Node.js**: 20+ (Claude CLI 依赖)

### 必需组件

1. **Telegram Bot Token**
   - 在 Telegram 搜索 @BotFather
   - 发送 `/newbot` 创建新机器人
   - 保存获得的 Token

2. **Telegram User ID**
   - 在 Telegram 搜索 @userinfobot
   - 发送任意消息获取你的 User ID

3. **Claude API Key** (二选一)
   - 官方: 从 [Anthropic Console](https://console.anthropic.com/) 获取
   - 代理: 使用自定义 API 端点

## Option 1: Docker (推荐)

最简单的安装方式，无需手动配置依赖。

### 步骤

```bash
# 1. 克隆项目
git clone https://github.com/xxx/cloudwork.git
cd cloudwork

# 2. 创建配置文件
cp config/.env.example config/.env

# 3. 编辑配置
nano config/.env
# 填入:
#   TELEGRAM_BOT_TOKEN=your_token
#   TELEGRAM_ALLOWED_USERS=your_user_id
#   ANTHROPIC_API_KEY=your_api_key

# 4. 构建并启动
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

### 管理命令

```bash
# 停止
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps

# 更新
git pull
docker-compose up -d --build
```

## Option 2: VPS 一键安装

适用于 Ubuntu/Debian VPS，自动安装所有依赖。

### 步骤

```bash
# 1. 以 root 身份运行安装脚本
curl -fsSL https://raw.githubusercontent.com/xxx/cloudwork/main/scripts/setup-vps.sh | sudo bash

# 2. 编辑配置
sudo nano /home/claude/cloudwork/config/.env

# 3. 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork  # 开机自启

# 4. 查看状态
sudo systemctl status cloudwork
```

### 管理命令

```bash
# 查看日志
sudo journalctl -u cloudwork -f

# 重启服务
sudo systemctl restart cloudwork

# 停止服务
sudo systemctl stop cloudwork

# 查看状态
sudo systemctl status cloudwork
```

## Option 3: 手动安装

适用于需要自定义配置的高级用户。

### 步骤

```bash
# 1. 安装系统依赖
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv nodejs npm expect

# macOS
brew install python@3.11 node

# 2. 安装 Claude CLI
npm install -g @anthropic-ai/claude-code

# 3. 克隆项目
git clone https://github.com/xxx/cloudwork.git
cd cloudwork

# 4. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 5. 安装 Python 依赖
pip install -r requirements.txt

# 6. 配置
cp config/.env.example config/.env
nano config/.env

# 7. 运行
python -m src.bot.main
```

### 使用 systemd (可选)

```bash
# 1. 复制服务文件
sudo cp scripts/cloudwork.service /etc/systemd/system/

# 2. 编辑服务文件，修改路径
sudo nano /etc/systemd/system/cloudwork.service

# 3. 重载 systemd
sudo systemctl daemon-reload

# 4. 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork
```

## Verification

安装完成后，验证安装是否成功：

1. 在 Telegram 中找到你的 Bot
2. 发送 `/start`
3. 应该收到欢迎消息

如果没有收到消息，检查：
- Bot Token 是否正确
- User ID 是否在白名单中
- 查看日志排查错误

## Troubleshooting

### 常见问题

**1. Claude CLI 无法安装**
```bash
# 确保 Node.js 版本 >= 20
node --version

# 使用国内镜像 (如果在中国)
npm config set registry https://registry.npmmirror.com
npm install -g @anthropic-ai/claude-code
```

**2. Bot 不响应**
- 检查 `TELEGRAM_BOT_TOKEN` 是否正确
- 检查 `TELEGRAM_ALLOWED_USERS` 是否包含你的 ID
- 查看日志: `docker-compose logs` 或 `journalctl -u cloudwork`

**3. Claude API 错误**
- 检查 API Key 是否有效
- 检查网络连接
- 如使用代理，确认 `ANTHROPIC_BASE_URL` 正确

**4. 权限问题**
```bash
# Docker
sudo usermod -aG docker $USER
# 重新登录

# VPS
sudo chown -R claude:claude /home/claude/cloudwork
```

## Next Steps

安装完成后，参考：
- [配置说明](CONFIGURATION.md) - 详细配置选项
- [命令参考](COMMANDS.md) - 所有 Telegram 命令
