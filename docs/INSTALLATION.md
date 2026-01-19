# 安装指南

CloudWork 支持三种安装方式：Docker、VPS 一键安装、手动安装。

## 📋 前置要求

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 20.04+、Debian 11+、macOS、或任何支持 Docker 的系统 |
| Python | 3.9+ (推荐 3.11) |
| Node.js | 20+ (Claude CLI 依赖) |
| 内存 | 最低 512MB，推荐 1GB+ |

### 准备以下信息

#### 1. Telegram Bot Token

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示创建机器人
4. 保存获得的 Token（格式：`123456789:ABCdef...`）

#### 2. Telegram User ID

1. 在 Telegram 搜索 `@userinfobot`
2. 发送任意消息
3. 记录返回的 User ID（纯数字）

#### 3. Claude API（二选一）

- **官方 API**: 从 [Anthropic Console](https://console.anthropic.com/) 获取
- **自定义代理**: 使用兼容的 API 端点

---

## 方式一：Docker 部署（推荐新手）

最简单的安装方式，无需手动配置依赖。

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 2. 创建配置文件
cp config/.env.example config/.env

# 3. 编辑配置
nano config/.env
```

填入配置：

```bash
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_ALLOWED_USERS=你的User ID
ANTHROPIC_API_KEY=你的API Key
```

```bash
# 4. 构建并启动
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

### 管理命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 更新到最新版本
git pull && docker-compose up -d --build
```

---

## 方式二：VPS 一键安装（推荐生产环境）

适用于 Ubuntu/Debian VPS，自动安装所有依赖。

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 2. 运行安装脚本（需要 root 权限）
sudo bash scripts/setup-vps.sh

# 3. 编辑配置
sudo nano /home/claude/cloudwork/config/.env

# 4. 启动服务
sudo systemctl start cloudwork

# 5. 设置开机自启
sudo systemctl enable cloudwork
```

### 管理命令

```bash
# 查看服务状态
sudo systemctl status cloudwork

# 查看实时日志
sudo journalctl -u cloudwork -f

# 重启服务
sudo systemctl restart cloudwork

# 停止服务
sudo systemctl stop cloudwork
```

### 安装脚本做了什么

- 创建 `claude` 用户
- 安装 Python 3.11、Node.js 20
- 安装 Claude CLI
- 复制项目到 `/home/claude/cloudwork`
- 创建 systemd 服务

---

## 方式三：手动安装（推荐开发者）

适用于需要自定义配置的高级用户。

### 安装步骤

#### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm
```

**macOS:**
```bash
brew install python@3.11 node
```

#### 2. 安装 Claude CLI

```bash
npm install -g @anthropic-ai/claude-code

# 验证安装
claude --version
```

#### 3. 克隆项目

```bash
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork
```

#### 4. 创建虚拟环境（可选但推荐）

```bash
python3.11 -m venv venv
source venv/bin/activate
```

#### 5. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 6. 配置环境变量

```bash
cp config/.env.example config/.env
nano config/.env
```

#### 7. 运行

```bash
python -m src.bot.main
```

### 配置 systemd 服务（可选）

```bash
# 1. 复制服务文件
sudo cp scripts/cloudwork.service /etc/systemd/system/

# 2. 根据需要编辑服务文件
sudo nano /etc/systemd/system/cloudwork.service

# 3. 重载 systemd
sudo systemctl daemon-reload

# 4. 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork
```

---

## ✅ 验证安装

安装完成后：

1. 打开 Telegram，找到你的 Bot
2. 发送 `/start`
3. 收到欢迎消息 = 安装成功！

如果没有收到消息，检查：

```bash
# Docker
docker-compose logs

# systemd
sudo journalctl -u cloudwork -n 50

# 手动运行
# 查看终端输出的错误信息
```

---

## 🛠️ 故障排除

### Claude CLI 安装失败

```bash
# 检查 Node.js 版本（需要 >= 20）
node --version

# 使用国内镜像（如果在中国）
npm config set registry https://registry.npmmirror.com
npm install -g @anthropic-ai/claude-code
```

### Bot 不响应

1. 检查 `TELEGRAM_BOT_TOKEN` 是否正确
2. 检查 `TELEGRAM_ALLOWED_USERS` 是否包含你的 User ID
3. 查看日志确认错误信息

### Claude API 错误

1. 检查 API Key 是否有效
2. 检查网络连接
3. 如使用代理，确认 `ANTHROPIC_BASE_URL` 正确

### 权限问题

```bash
# VPS 部署时确保权限正确
sudo chown -R claude:claude /home/claude/cloudwork

# Docker 用户组
sudo usermod -aG docker $USER
# 然后重新登录
```

---

## 📚 下一步

安装完成后：

- [快速开始](../QUICK_START.md) - 基本使用教程
- [命令参考](COMMANDS.md) - 所有 Telegram 命令
