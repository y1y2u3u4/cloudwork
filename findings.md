# CloudWork 发现与研究记录

> 记录迁移过程中的发现、技术研究和关键信息

**更新时间**: 2026-01-19

---

## 现有系统分析

### 核心功能模块 (从 ROADMAP.md 提取)

| 功能 | 实现位置 | 关键点 |
|------|----------|--------|
| Syncthing 文件同步 | systemd service | 端口 8384, 22000 |
| 多模型支持 | `--model` 参数 | sonnet/opus/haiku |
| 执行模式 | `--dangerously-skip-permissions` | auto/plan |
| 项目发现 | 扫描 tasks/ 目录 | 检测 CLAUDE.md |
| 流式输出 | `--output-format stream-json` | unbuffer |
| 交互式问答 | stdin 管道 | tool_use 事件 |
| 多会话管理 | sessions.json | 30分钟自动归档 |
| 设置菜单 | Inline Keyboard | 统一配置入口 |

### 配置项清单

**必需配置**:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USERS`

**Claude API 配置 (二选一)**:
- 官方: `ANTHROPIC_API_KEY`
- 代理: `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`

**可选配置**:
- `WORK_DIR` (默认: `/home/claude/vps-cloud-runner`)
- `COMMAND_TIMEOUT` (默认: 300)
- `DEFAULT_MODEL` (默认: sonnet)
- `DEFAULT_MODE` (默认: auto)
- `AUTO_ARCHIVE_MINUTES` (默认: 30)

### 文件结构分析

```
当前结构:
vps-cloud-runner/
├── bots/telegram_bot.py    # 主程序 2600+ 行
├── config/.env             # 敏感配置 (需保护)
├── data/sessions.json      # 会话数据
├── logs/                   # 日志目录
├── scripts/                # systemd 服务配置
└── tasks/                  # 工作空间 (混杂个人项目)
```

---

## 技术研究

### Docker 基础镜像选择

**选择**: `python:3.11-slim`

原因:
- 官方维护，稳定可靠
- slim 版本体积小 (~150MB)
- Python 3.11 性能提升 + 新特性

### Claude CLI 安装

```dockerfile
# Node.js 安装 (Claude CLI 依赖)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Claude Code CLI 安装
RUN npm install -g @anthropic-ai/claude-code
```

### 持久化方案

**推荐: Volume 挂载**

```yaml
volumes:
  - ./data:/app/data              # Bot 会话
  - ./workspace:/app/workspace    # 工作空间
  - claude-sessions:/root/.claude # CLI 会话
```

关键路径:
- Bot 会话: `/app/data/sessions.json`
- Claude CLI: `/root/.claude/` (包含会话历史)

---

## 兼容性注意

### Python 3.9 类型注解

VPS 可能运行 Python 3.9，需使用兼容写法:

```python
# ❌ Python 3.10+ 语法
def func(x: str | None) -> tuple[str, str]:
    pass

# ✅ Python 3.9 兼容
from typing import Optional, Tuple
def func(x: Optional[str]) -> Tuple[str, str]:
    pass
```

### pydantic-settings

用于配置管理:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str

    class Config:
        env_file = ".env"
```

---

## 待确认事项

- [ ] Railway Pro 计划成本确认
- [ ] 是否需要支持 Syncthing (VPS 专属)
- [ ] 多用户隔离需求

---

## 参考资源

- [Claude Code CLI 文档](https://docs.anthropic.com/claude-code)
- [python-telegram-bot 文档](https://python-telegram-bot.org/)
- [Railway 部署指南](https://docs.railway.app/)
