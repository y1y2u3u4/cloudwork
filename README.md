# ☁️ CloudWork

> Run Claude Code in the cloud, control it from anywhere via Telegram.

**CloudWork** 是一个云端 Claude Code 工作空间，让你通过 Telegram Bot 远程触发 AI 编程任务。无论在手机上还是电脑前，随时随地都能让 Claude 帮你写代码。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🤖 **多会话管理** | 每用户独立会话，支持切换和归档 |
| 📱 **Telegram 控制** | 手机即可触发编程任务 |
| 🔄 **实时流式输出** | 实时查看 Claude 执行过程 |
| 💬 **交互式问答** | 响应 Claude 的确认请求 |
| ⚡ **多模型支持** | sonnet / opus / haiku 随时切换 |
| 📁 **项目管理** | 支持多项目切换 |
| 🔐 **用户白名单** | 安全的访问控制 |

## 🚀 快速开始

### 方式一：VPS 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 2. 运行安装脚本
sudo bash scripts/setup-vps.sh

# 3. 配置环境变量
sudo nano /home/claude/cloudwork/config/.env

# 4. 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork
```

### 方式二：Docker 部署

```bash
# 1. 克隆项目
git clone https://github.com/y1y2u3u4/cloudwork.git
cd cloudwork

# 2. 配置
cp config/.env.example config/.env
nano config/.env  # 填入你的 Token

# 3. 启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 方式三：手动安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp config/.env.example config/.env
nano config/.env

# 3. 运行
python -m src.bot.main
```

📖 详细安装说明：[安装指南](docs/INSTALLATION.md)

## ⚙️ 配置说明

### 必需配置

创建 `config/.env` 文件：

```bash
# Telegram Bot Token (从 @BotFather 获取)
TELEGRAM_BOT_TOKEN=your_bot_token

# 授权用户 ID (从 @userinfobot 获取，多个用逗号分隔)
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

### Claude API 配置（二选一）

**官方 API:**
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**自定义代理:**
```bash
ANTHROPIC_BASE_URL=https://your-proxy.com/api
ANTHROPIC_AUTH_TOKEN=your_token
```

### 可选配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | `sonnet` | 默认模型 (sonnet/opus/haiku) |
| `DEFAULT_MODE` | `auto` | 执行模式 (auto/plan) |
| `COMMAND_TIMEOUT` | `300` | 命令超时秒数 |
| `AUTO_ARCHIVE_MINUTES` | `30` | 会话自动归档时间 |

## 🎮 Telegram 命令

### 基础命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/start` | 显示帮助 | `/start` |
| `/run <提示>` | 独立执行任务 | `/run 写个排序算法` |
| `/new [名称]` | 创建新会话 | `/new Flask项目` |
| `/sessions` | 查看/切换会话 | `/sessions` |
| `/archived` | 查看归档会话 | `/archived` |

### 设置命令

| 命令 | 功能 |
|------|------|
| `/settings` | 打开设置菜单 |
| `/model` | 切换 Claude 模型 |
| `/mode` | 切换执行模式 |
| `/project` | 切换项目 |

### 对话方式

- **直接发消息** → 在当前会话中对话
- **回复历史消息** → 自动切换到该消息的会话

📖 完整命令参考：[命令文档](docs/COMMANDS.md)

## 📁 项目结构

```
cloudwork/
├── src/
│   ├── bot/
│   │   ├── main.py           # Bot 主入口
│   │   ├── handlers/         # 命令处理器
│   │   └── services/         # 核心服务
│   └── utils/                # 工具函数
├── config/
│   └── .env.example          # 配置模板
├── data/                     # 会话数据
├── workspace/                # 项目工作空间
├── scripts/
│   ├── setup-vps.sh          # VPS 安装脚本
│   └── cloudwork.service     # systemd 服务
├── docs/                     # 文档
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📚 文档

- [快速开始](QUICK_START.md) - 5分钟上手
- [安装指南](docs/INSTALLATION.md) - 详细安装步骤
- [命令参考](docs/COMMANDS.md) - 所有 Telegram 命令

## 🛠️ 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 代码格式化
black src/
```

## 📄 License

MIT License

## 💬 支持

- 提交 Issue: [GitHub Issues](https://github.com/y1y2u3u4/cloudwork/issues)
