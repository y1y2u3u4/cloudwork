# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cloudwork 是一个通过 Telegram Bot 远程触发 Claude Code 的自动化系统。支持 VPS 直接执行和通过 Tailscale 内网代理到本地 Mac 执行两种模式。附带一个 Tauri + React 桌面客户端。

## Architecture

```
手机 Telegram → VPS Bot (Telegram polling) → Claude CLI (subprocess, stream-json)
                                           → 或经 Tailscale 代理到 Mac Desktop API (FastAPI SSE)
```

核心数据流：用户在 Telegram 发消息 → `handlers/messages.py` 接收 → `services/claude.py` 构建命令并启动 `asyncio.create_subprocess_exec` 执行 `claude -p --output-format stream-json` → 解析 JSON 事件流 → 通过 Telegram 消息更新实时反馈进度。

**关键设计决策：**
- Bot 直接运行 Syncthing 同步目录的代码，修改后通过 Syncthing 自动同步到 VPS，再重启 systemd 服务生效
- 使用 `unbuffer` 包装 Claude CLI 避免行缓冲问题
- stream-json 事件类型：`system`(session_id+tools) → `assistant`(text+tool_use) → `user`(tool_result) → `result`(最终结果)
- 会话通过 `--resume <session_id>` 实现多轮对话，session_id 从 system 事件中获取

## Key Components

```
src/
├── bot/
│   ├── main.py                # 主入口，注册 handlers，启动 polling
│   ├── handlers/
│   │   ├── commands.py        # Telegram 命令 (/model, /project, /target, /cron, /seo 等)
│   │   ├── messages.py        # 文本+图片消息处理，调用 ClaudeExecutor
│   │   └── callbacks.py       # InlineKeyboard 按钮回调
│   └── services/
│       ├── claude.py          # ClaudeExecutor - 构建命令、流式执行、本地节点代理
│       ├── session.py         # SessionManager - 会话/用户状态持久化 (data/sessions.json)
│       ├── task.py            # TaskManager - 运行中任务追踪 (RunningTask dataclass)
│       ├── tool_display.py    # 工具调用格式化显示
│       ├── memory.py          # 记忆系统 (learned/ + MEMORY.md)
│       ├── cron_notifier.py   # Cron 任务输出监听+通知
│       ├── cron_config.py     # Cron 配置管理
│       └── skills.py          # 技能系统 (SEO 挖掘等)
├── utils/
│   ├── config.py              # pydantic-settings 配置 (Settings 类)
│   ├── auth.py                # Telegram 用户认证
│   └── formatters.py          # Markdown 转义、消息截断、进度格式化
desktop/
├── api/main.py                # FastAPI Desktop API Bridge (端口 2026)
├── src/                       # React + Tauri 前端 (TypeScript)
└── src-tauri/                 # Tauri Rust 后端
```

## Commands

```bash
# 本地运行 Bot
export $(cat config/.env | xargs) && python -m src.bot.main

# SSH 到 VPS
source config/.env && sshpass -p "$VPS_PASSWORD" ssh ${VPS_USER}@${VPS_HOST}

# VPS 上重启 Bot（代码通过 Syncthing 自动同步，只需重启）
sudo systemctl restart cloudwork    # 或无 sudo：kill $(pgrep -f "src.bot.main")
journalctl -u cloudwork -f          # 实时日志

# 本地启动 Desktop API（必须覆盖 VPS 路径）
LOCAL_ROOT="/Users/zhanggongqing/project/孵化项目/cloudwork"
cd "$LOCAL_ROOT" && WORK_DIR="$LOCAL_ROOT" DATA_DIR="$LOCAL_ROOT/data" \
  WORKSPACE_DIR="$LOCAL_ROOT/workspace" API_HOST=0.0.0.0 python desktop/api/main.py
```

## Syncthing 同步

- 本地: `/Users/zhanggongqing/project/孵化项目/cloudwork`
- VPS: `/home/claude/vps-cloud-runner/tasks/cloudwork`
- "folder marker missing" 错误 → `mkdir -p .stfolder`
- 文件丢失 → `source config/.env && sshpass -p "$VPS_PASSWORD" scp -r ${VPS_USER}@${VPS_HOST}:/home/claude/vps-cloud-runner/tasks/cloudwork/src ./`

## systemd 服务

```ini
# /etc/systemd/system/cloudwork.service
[Service]
WorkingDirectory=/home/claude/vps-cloud-runner/tasks/cloudwork
EnvironmentFile=/home/claude/vps-cloud-runner/tasks/cloudwork/config/.env
ExecStart=/usr/bin/python3 -m src.bot.main
Restart=always
RestartSec=10
```

配置了 `Restart=always`，kill 进程后 systemd 会在 10 秒后自动重启。

## Python 兼容性

**VPS 运行 Python 3.9**，类型注解必须使用 `typing` 模块：
```python
from typing import Optional, Tuple, Dict, List
def func(x: Optional[str]) -> Tuple[str, str]:  # 不要用 str | None 或 tuple[str, str]
```

## Environment Variables

配置文件: `config/.env`（通过 pydantic-settings 加载）

| 变量 | 用途 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（必填）|
| `TELEGRAM_ALLOWED_USERS` | 授权用户 ID，逗号分隔（必填）|
| `ANTHROPIC_BASE_URL` | 自定义 API 端点 |
| `ANTHROPIC_AUTH_TOKEN` | 自定义端点认证 Token |
| `VPS_HOST` / `VPS_USER` / `VPS_PASSWORD` | VPS SSH 连接 |
| `LOCAL_NODE_URL` | 本地节点 Desktop API 地址 |
| `LOCAL_API_TOKEN` | Desktop API 认证 Token |

## 本地节点执行

通过 Tailscale 内网穿透代理到本地 Mac：

```
手机 Telegram → VPS Bot (100.96.65.52) → Tailscale → Mac Desktop API (100.90.229.128:2026)
```

Telegram 命令：`/target local http://100.90.229.128:2026` / `/target vps`

> `.env` 中路径是 VPS 的 `/home/claude/...`，本地启动 Desktop API 时必须覆盖为本地路径。

## Git Push（VPS → GitHub）

```bash
# 使用 SSH (Deploy Key 已配置)
git remote set-url origin git@github.com:y1y2u3u4/cloudwork.git
git add -A && git commit -m "描述" && git push origin main
```

## Memory System

记忆文件存储在 `data/memory/`，通过 CLAUDE.md 索引触发读取：
- **读取**: 遇到相关场景时先读取 `data/memory/learned/<topic>.md`
- **写入**: Bug 修复、技术决策 → 创建 `data/memory/learned/<问题简述>.md`
- **遗忘**: `/memory forget` 预览，`/memory forget --confirm` 清理（<25 分）
- **持续学习**: 自动提取 error_resolution / user_correction / workaround 等模式
