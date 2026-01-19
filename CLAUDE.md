# CLAUDE.md

CloudWork 项目开发指南，供 Claude Code 参考。

## 项目概述

CloudWork 是一个云端 Claude Code 工作空间，通过 Telegram Bot 远程触发 AI 编程任务。

## 目录结构

```
cloudwork/
├── src/
│   ├── bot/
│   │   ├── main.py           # Bot 主入口
│   │   ├── handlers/         # 命令/消息/回调处理
│   │   │   ├── commands.py
│   │   │   ├── messages.py
│   │   │   └── callbacks.py
│   │   └── services/         # 核心服务
│   │       ├── claude.py     # Claude CLI 执行
│   │       ├── session.py    # 会话管理
│   │       └── task.py       # 任务队列
│   └── utils/
│       ├── config.py         # 配置管理
│       ├── auth.py           # 用户认证
│       └── formatters.py     # 输出格式化
├── config/
│   └── .env.example          # 配置模板
├── data/                     # 会话数据 (运行时)
├── workspace/                # 任务工作空间 (运行时)
├── scripts/
│   ├── setup-vps.sh          # VPS 安装脚本
│   └── claude-bot.service    # systemd 服务
├── docs/                     # 文档
├── tests/                    # 测试
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 本地运行 (需要配置 config/.env)
cd src && python -m bot.main

# Docker 构建
docker build -t cloudwork .

# Docker 运行
docker-compose up -d
```

## 代码规范

### Python 版本兼容

目标兼容 Python 3.9+，类型注解使用兼容写法：

```python
# ✅ 正确 (Python 3.9 兼容)
from typing import Optional, Tuple, List, Dict

def func(x: Optional[str]) -> Tuple[str, str]:
    pass

# ❌ 避免 (Python 3.10+ 语法)
def func(x: str | None) -> tuple[str, str]:
    pass
```

### 模块导入

```python
# src/bot/handlers/commands.py
from ..services.claude import execute_claude
from ..services.session import SessionManager
from ...utils.config import settings
```

### 配置访问

```python
from src.utils.config import settings

# 使用配置
token = settings.telegram_bot_token
model = settings.default_model
```

## 核心功能

1. **多会话管理**: 每用户独立会话，30分钟无活动自动归档
2. **流式输出**: 实时显示 Claude 执行过程
3. **交互式问答**: 响应 Claude 的用户确认请求
4. **多模型支持**: sonnet / opus / haiku 动态切换
5. **项目发现**: 自动扫描 workspace 目录中的项目

## 环境变量

必需:
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `TELEGRAM_ALLOWED_USERS`: 授权用户 ID (逗号分隔)

Claude API (二选一):
- `ANTHROPIC_API_KEY`: 官方 API Key
- `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`: 自定义代理

可选:
- `DEFAULT_MODEL`: 默认模型 (sonnet)
- `DEFAULT_MODE`: 执行模式 (auto)
- `COMMAND_TIMEOUT`: 命令超时秒数 (300)

## 部署注意事项

### 服务运行用户 (重要!)

**服务必须以 `claude` 用户运行，不能以 root 运行！**

原因：Claude CLI 的 `--dangerously-skip-permissions` 参数在 root 权限下会被拒绝执行，这是 Claude CLI 的安全限制。

正确的 systemd 服务配置：
```ini
[Service]
User=claude
Group=claude
WorkingDirectory=/home/claude/cloudwork
EnvironmentFile=/home/claude/cloudwork/config/.env
Environment=PYTHONPATH=/home/claude/cloudwork
ExecStart=/usr/bin/python3 -m src.bot.main
```

### VPS 部署

1. 确保 `claude` 用户存在：
   ```bash
   useradd -m -s /bin/bash claude
   ```

2. 项目目录权限：
   ```bash
   chown -R claude:claude /home/claude/cloudwork
   ```

3. 启动服务：
   ```bash
   systemctl daemon-reload
   systemctl start cloudwork
   systemctl enable cloudwork
   ```

## 测试

```bash
# 运行测试
pytest tests/

# 带覆盖率
pytest --cov=src tests/
```
