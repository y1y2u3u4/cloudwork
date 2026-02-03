# ☁️ CloudWork

> Run Claude Code in the cloud, control it from anywhere via Telegram.

**CloudWork** 是一个云端 Claude Code 工作空间，让你通过 Telegram Bot 远程触发 AI 编程任务。无论在手机上还是电脑前，随时随地都能让 Claude 帮你写代码。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 **多会话管理** | 每用户独立会话，支持切换、归档、回复历史消息自动切换 |
| 📱 **Telegram 控制** | 手机即可触发编程任务 |
| 🔄 **实时流式输出** | 实时查看 Claude 执行过程 |
| 💬 **交互式问答** | 响应 Claude 的确认请求 |
| ⚡ **多模型支持** | sonnet / opus / haiku 随时切换 |
| 📁 **项目管理** | 支持多项目切换 |
| 🖼️ **图片分析** | 发送图片给 Claude 分析 |
| 🏠 **本地节点执行** | 通过 Tailscale 远程控制本地 Mac 执行 |
| 🔐 **用户白名单** | 安全的访问控制 |

## 🚀 快速开始

### 1. 准备工作

| 项目 | 获取方式 |
|------|----------|
| **Telegram Bot Token** | Telegram 搜索 `@BotFather`，发送 `/newbot` |
| **你的 User ID** | Telegram 搜索 `@userinfobot`，发送任意消息 |
| **Claude API** | [Anthropic Console](https://console.anthropic.com/) 或自定义代理 |

### 2. 安装

```bash
# 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 安装依赖
pip install -r requirements.txt

# 配置
cp config/.env.example config/.env
nano config/.env  # 填入你的 Token
```

### 3. 配置 (.env)

```bash
# 必需配置
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_ALLOWED_USERS=你的User ID

# Claude API (二选一)
ANTHROPIC_API_KEY=sk-ant-xxxxx           # 官方 API
# ANTHROPIC_BASE_URL=https://proxy.com   # 或自定义代理
# ANTHROPIC_AUTH_TOKEN=your_token
```

### 4. 启动

```bash
python -m src.bot.main
```

### 5. 验证

在 Telegram 找到你的 Bot，发送 `/start`，收到回复即成功！

```bash
# 可选：验证配置是否正确
python scripts/check-config.py
```

## 🎮 Telegram 命令

### 核心命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/start` | 显示帮助 | `/start` |
| `/run <提示>` | 独立执行（不影响会话）| `/run 写个排序算法` |
| `/new [名称]` | 创建新会话 | `/new Flask项目` |
| `/sessions` | 查看/切换会话 | `/sessions` |
| `/model` | 切换模型 | `/model` |
| `/target` | 切换执行目标 (VPS/本地) | `/target` |

### 对话方式

| 方式 | 说明 |
|------|------|
| **直接发消息** | 在当前会话中继续对话 |
| **回复历史消息** | 自动切换到该消息的会话 |
| **发送图片** | 图片会下载供 Claude 分析 |

📖 完整命令：[docs/COMMANDS.md](docs/COMMANDS.md)

## 🚀 生产部署

### systemd 服务（推荐）

```bash
sudo cp scripts/cloudwork.service /etc/systemd/system/
sudo systemctl start cloudwork
sudo systemctl enable cloudwork
```

### Docker

```bash
docker-compose up -d
```

### VPS 一键安装

```bash
sudo bash scripts/setup-vps.sh
```

📖 详细部署：[docs/INSTALLATION.md](docs/INSTALLATION.md)

## ⚙️ 可选配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | `sonnet` | 默认模型 (sonnet/opus/haiku) |
| `DEFAULT_MODE` | `auto` | 执行模式 (auto/plan) |
| `COMMAND_TIMEOUT` | `300` | 命令超时秒数 |
| `AUTO_ARCHIVE_MINUTES` | `30` | 会话自动归档时间 |

### 本地节点执行（高级）

通过 Tailscale 让 VPS Bot 控制本地 Mac 执行任务：

```bash
# config/.env
LOCAL_NODE_URL=http://100.90.229.128:2026
LOCAL_API_TOKEN=your_token

# Telegram 中切换
/target local http://your-tailscale-ip:2026
```

📖 详细配置：[docs/local-node-execution.md](docs/local-node-execution.md)

## 📁 项目结构

```
cloudwork/
├── src/bot/              # Bot 核心代码
│   ├── main.py           # 主入口
│   ├── handlers/         # 命令处理器
│   └── services/         # Claude/会话/任务服务
├── config/.env           # 配置文件
├── data/sessions.json    # 会话数据
├── workspace/            # 项目工作空间
└── scripts/              # 安装和管理脚本
```

## 🛠️ 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 验证配置
python scripts/check-config.py

# 运行测试
pytest tests/
```

## 📄 License

MIT License

## 💬 支持

- 提交 Issue: [GitHub Issues](https://github.com/y1y2u3u4/cloudwork/issues)
