# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cloudwork 是一个在 VPS 上运行 Claude Code 的远程自动化系统，通过 Telegram Bot 远程触发任务，支持多会话管理。

## Architecture

```
┌─────────────────┐       ┌─────────────────────────────────┐
│   Local macOS   │◄─────►│        VPS Server               │
│   (开发环境)     │ Sync  │      (104.244.93.244)           │
│   cloudwork/    │ Thing │  tasks/cloudwork/ ← Bot运行目录  │
└─────────────────┘       └─────────────────────────────────┘
                                        │
                                        │ systemd (claude-bot.service)
                                        ▼
                                ┌─────────────────┐
                                │  src/bot/main.py │
                                │    (主入口)      │
                                └─────────────────┘
                                        │
                                asyncio subprocess
                                        ▼
                                ┌─────────────────┐
                                │   Claude CLI    │
                                │  (claude -p)    │
                                └─────────────────┘
```

## Syncthing 同步

**同步目录映射：**
- 本地: `/Users/zhanggongqing/project/孵化项目/cloudwork`
- VPS: `/home/claude/vps-cloud-runner/tasks/cloudwork`

**重要：Bot 直接运行 Syncthing 同步目录的代码！**

**常见问题排查：**
- 如果 Syncthing 显示 "folder marker missing" 错误，需要重建 `.stfolder` 目录：
  ```bash
  mkdir -p /Users/zhanggongqing/project/孵化项目/cloudwork/.stfolder
  ```
- 如果本地文件丢失，可能是同步冲突，从 VPS 拉取：
  ```bash
  source config/.env && sshpass -p "$VPS_PASSWORD" scp -r ${VPS_USER}@${VPS_HOST}:/home/claude/vps-cloud-runner/tasks/cloudwork/src ./
  ```

## Key Components

```
src/
├── bot/
│   ├── main.py              # 主入口（python -m src.bot.main）
│   ├── handlers/
│   │   ├── commands.py      # /start, /cancel, /project 等命令
│   │   ├── messages.py      # 消息处理（调用 Claude CLI）
│   │   └── callbacks.py     # 按钮回调处理
│   └── services/
│       ├── claude.py        # Claude CLI 执行器
│       ├── session.py       # 会话管理
│       ├── task.py          # 任务管理
│       └── skills.py        # 技能系统
└── utils/
    ├── config.py            # 配置管理（pydantic-settings）
    ├── auth.py              # 用户认证
    └── formatters.py        # 输出格式化
```

- **data/sessions.json**: 会话持久化存储
- **config/.env**: 环境变量配置

## Commands

### VPS 操作
```bash
# SSH 到 VPS
source config/.env && sshpass -p "$VPS_PASSWORD" ssh ${VPS_USER}@${VPS_HOST}

# Bot 管理（在 VPS 上执行）
systemctl restart claude-bot    # 重启 Bot（代码通过 Syncthing 自动同步，只需重启）
systemctl status claude-bot     # 查看状态
journalctl -u claude-bot -f     # 实时日志

# 手动同步代码（通常不需要，Syncthing 会自动同步）
source config/.env && sshpass -p "$VPS_PASSWORD" scp -r src/* ${VPS_USER}@${VPS_HOST}:/home/claude/vps-cloud-runner/tasks/cloudwork/src/
```

### systemd 服务配置
```ini
# /etc/systemd/system/claude-bot.service
[Service]
WorkingDirectory=/home/claude/vps-cloud-runner/tasks/cloudwork
EnvironmentFile=/home/claude/vps-cloud-runner/tasks/cloudwork/config/.env
ExecStart=/usr/bin/python3 -m src.bot.main
Restart=always
RestartSec=10
```

### 重启 Bot 服务

**方法 1: 使用 sudo（需要 root 权限）**
```bash
sudo systemctl restart claude-bot
```

**方法 2: Kill 进程让 systemd 自动重启（无需 sudo）**

由于服务配置了 `Restart=always`，可以直接 kill 进程，systemd 会在 10 秒后自动重启：
```bash
# 查找并终止 Bot 进程
kill $(pgrep -f "src.bot.main")

# 等待 12 秒后检查新进程
sleep 12 && ps aux | grep "src.bot.main" | grep -v grep
```

**验证重启成功**
```bash
# 检查进程启动时间（应该是最近）
ps aux | grep "src.bot.main" | grep -v grep

# 检查服务状态
systemctl status claude-bot
```

### Git Push（从 VPS 推送到 GitHub）

VPS 使用 SSH 方式推送代码到 GitHub：

```bash
# 远程仓库配置（已配置）
git remote set-url origin git@github.com:y1y2u3u4/cloudwork.git

# 推送代码
git add -A && git commit -m "描述" && git push origin main
```

**SSH 密钥：** VPS 的 SSH 公钥 (`~/.ssh/id_ed25519.pub`) 已添加到 GitHub Deploy Keys。

### 本地测试
```bash
# 需要先设置环境变量
export $(cat config/.env | xargs)
python -m src.bot.main
```

## Environment Variables

| 变量 | 用途 |
|------|------|
| `ANTHROPIC_BASE_URL` | 自定义 API 端点 |
| `ANTHROPIC_AUTH_TOKEN` | 自定义端点认证 Token |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_ALLOWED_USERS` | 授权用户 ID（逗号分隔）|
| `VPS_HOST` / `VPS_USER` / `VPS_PASSWORD` | VPS SSH 连接信息 |

## Telegram Bot Commands

| 命令 | 功能 |
|------|------|
| `/start` | 帮助信息 |
| `/run <prompt>` | 独立执行（不影响会话）|
| `/sessions` | 查看和切换会话 |
| `/new [名称]` | 创建新会话 |
| `/archived` | 查看归档会话 |
| `/delete <会话ID>` | 删除会话 |
| 直接发消息 | 在当前活跃会话中对话 |
| 回复历史消息 | 自动切换到该消息的会话 |

## Session Management

会话数据结构在 `data/sessions.json`：
- 每个用户有独立的会话列表
- 会话 30 分钟无活动自动归档
- 支持 AI 自动命名（根据首条消息）
- 通过按钮或回复消息切换会话

## Python 兼容性

VPS 运行 Python 3.9，类型注解需使用：
```python
from typing import Optional, Tuple
def func(x: Optional[str]) -> Tuple[str, str]:  # 不要用 str | None 或 tuple[str, str]
```

## Memory System

### 读取记忆
遇到以下场景时，先读取对应文件：

- **Python 类型注解** → `data/memory/learned/python-3-9-类型注解兼容性.md`
- **工具显示问题** → `data/memory/learned/tool-display-周期性更新覆盖问题.md`
- **记忆系统设计** → `data/memory/learned/markdown-记忆系统-vs-向量数据库.md`

### 写入记忆
当发现以下情况时，主动记录：

1. **Bug 修复经验**: 创建 `data/memory/learned/<问题简述>.md`，包含问题、原因、解决方案
2. **技术决策**: 记录为什么选择某个方案而不是另一个
3. **项目特有知识**: 不在代码中明显体现但重要的上下文

记录后，在上面的"读取记忆"列表中添加一行触发规则。
