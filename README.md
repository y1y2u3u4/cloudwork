# ☁️ CloudWork

> Run Claude Code in the cloud, control it from anywhere via Telegram.

**CloudWork** 是一个云端 Claude Code 工作空间，让你可以通过 Telegram Bot 远程触发 AI 编程任务。

## ✨ Features

- 🤖 **多会话管理** - 每用户独立会话，支持会话切换和归档
- 📱 **Telegram Bot 控制** - 随时随地通过手机触发任务
- 🔄 **实时流式输出** - 实时查看 Claude 执行过程
- 💬 **交互式问答** - 响应 Claude 的用户确认请求
- ⚡ **多模型支持** - 动态切换 sonnet / opus / haiku
- 📁 **项目发现** - 自动扫描工作空间项目
- 🔐 **用户白名单** - 安全访问控制

## 🚀 Quick Start

### Option 1: Docker (推荐)

```bash
# 克隆项目
git clone https://github.com/xxx/cloudwork.git
cd cloudwork

# 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入你的 Token

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### Option 2: VPS 一键安装

```bash
# Ubuntu 20.04+ 一键安装
curl -fsSL https://raw.githubusercontent.com/xxx/cloudwork/main/scripts/setup-vps.sh | sudo bash

# 编辑配置
sudo nano /home/claude/cloudwork/config/.env

# 启动服务
sudo systemctl start cloudwork
sudo systemctl enable cloudwork
```

### Option 3: 手动安装

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp config/.env.example config/.env
# 编辑 config/.env

# 运行
python -m src.bot.main
```

## 📖 Configuration

### 必需配置

| 变量 | 说明 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token (从 @BotFather 获取) |
| `TELEGRAM_ALLOWED_USERS` | 授权用户 ID (逗号分隔，从 @userinfobot 获取) |

### Claude API (二选一)

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

## 🎮 Telegram Commands

| 命令 | 功能 |
|------|------|
| `/start` | 显示帮助信息 |
| `/run <prompt>` | 独立执行任务 (不影响会话) |
| `/sessions` | 查看和切换会话 |
| `/new [名称]` | 创建新会话 |
| `/archived` | 查看归档会话 |
| `/delete <ID>` | 删除会话 |
| `/project` | 查看和切换项目 |
| `/model` | 切换 Claude 模型 |
| `/mode` | 切换执行模式 |
| `/settings` | 打开设置菜单 |

**对话方式:**
- 直接发消息 → 在当前活跃会话中对话
- 回复历史消息 → 自动切换到该消息的会话

## 📁 Project Structure

```
cloudwork/
├── src/
│   ├── bot/
│   │   ├── main.py           # Bot 主入口
│   │   ├── handlers/         # 命令/消息处理
│   │   └── services/         # 核心服务
│   └── utils/                # 工具函数
├── config/
│   └── .env.example          # 配置模板
├── data/                     # 会话数据
├── workspace/                # 任务工作空间
├── scripts/
│   ├── setup-vps.sh          # VPS 安装脚本
│   └── cloudwork.service     # systemd 服务
├── docs/                     # 文档
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 📚 Documentation

- [安装指南](docs/INSTALLATION.md)
- [配置说明](docs/CONFIGURATION.md)
- [Docker 部署](docs/DOCKER_DEPLOY.md)
- [VPS 部署](docs/VPS_DEPLOY.md)
- [命令参考](docs/COMMANDS.md)
- [架构说明](docs/ARCHITECTURE.md)

## 🛠️ Development

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio

# 运行测试
pytest tests/

# 代码格式化
black src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🤝 Contributing

欢迎贡献代码！请阅读 [贡献指南](CONTRIBUTING.md)。

## 💬 Support

- 提交 Issue: [GitHub Issues](https://github.com/xxx/cloudwork/issues)
- Telegram 群组: [待建立]
