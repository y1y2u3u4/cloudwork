# CloudWork v2 详细开发计划

> **目标**: 融合四大项目优势，打造云端+桌面端双模式超级 Agent
> **周期**: 10 周 (可并行开发缩短至 7 周)
> **原则**: 价值优先、增量交付、每周可用

---

## 一、四大项目优势提炼

### 1.1 可落地的核心能力

| 来源项目 | 核心能力 | 价值评分 | 落地难度 | 优先级 |
|----------|----------|----------|----------|--------|
| **ClawdBot** | 消息节流 + 智能分块 | ⭐⭐⭐⭐⭐ | 低 | P0 |
| **ClawdBot** | LanceDB 长期记忆 | ⭐⭐⭐⭐⭐ | 中 | P0 |
| **ClawdBot** | MCP 工具生态 | ⭐⭐⭐⭐ | 中 | P1 |
| **everything-cc** | 9 个专业子代理 | ⭐⭐⭐⭐⭐ | 低 | P0 |
| **everything-cc** | 持续学习系统 | ⭐⭐⭐⭐ | 中 | P1 |
| **everything-cc** | 验证循环 (/verify) | ⭐⭐⭐⭐⭐ | 低 | P0 |
| **everything-cc** | Hook 自动化 | ⭐⭐⭐⭐ | 中 | P1 |
| **WorkAny** | Plan-Execute 模式 | ⭐⭐⭐⭐ | 中 | P1 |
| **WorkAny** | 强制备份机制 | ⭐⭐⭐⭐⭐ | 低 | P0 |
| **WorkAny** | 桌面端 UI | ⭐⭐⭐⭐⭐ | 高 | P2 |
| **WorkAny** | Artifact 预览 | ⭐⭐⭐⭐ | 高 | P2 |

### 1.2 CloudWork 已有优势 (保持)

| 能力 | 现状 | 策略 |
|------|------|------|
| Telegram 远程访问 | ✅ 完善 | 保持，增强体验 |
| Cron 定时任务 | ✅ 完善 | 保持，增加可视化 |
| Freqtrade Trading | ✅ 集成 | 增强 MCP 封装 |
| 多会话管理 | ✅ 完善 | 增加记忆关联 |
| 极简部署 | ✅ 优势 | 保持 |

---

## 二、分阶段开发计划

### Phase 0: 快速增强 (Week 1) - 立即见效

**目标**: 用最小改动获得最大体验提升

```
Week 1 任务:
├─ Day 1-2: 消息体验优化
│   ├─ [P0] 消息编辑节流 (300ms throttle)
│   ├─ [P0] 工具详情展示 (📖 Read → file.py)
│   └─ [P0] Markdown 智能分块 (不截断代码块)
│
├─ Day 3-4: 安全增强
│   ├─ [P0] 强制备份指令注入
│   └─ [P0] 危险命令预警 (rm -rf, git push --force)
│
└─ Day 5: 快捷命令
    ├─ [P0] /verify - 运行构建+测试+lint
    └─ [P0] /review - 快速代码审查
```

**交付物**:
- [x] `src/bot/services/stream_throttle.py` - 消息节流器
- [x] `src/bot/services/tool_formatter.py` - 工具详情格式化
- [x] `src/bot/services/safety.py` - 安全检查
- [x] `src/bot/handlers/commands.py` - 新增 /verify, /review

**验收标准**:
- 消息不再频繁闪烁
- 工具调用显示详细参数
- 删除操作有备份提示
- /verify 可运行项目验证

---

### Phase 1: 子代理系统 (Week 2-3) - 核心价值

**目标**: 实现专业化子代理，提升开发效率

```
Week 2 任务:
├─ Day 1-2: 代理框架
│   ├─ [P0] Agent 基类设计
│   ├─ [P0] 代理注册中心
│   └─ [P0] YAML 配置加载
│
├─ Day 3-4: 核心代理实现
│   ├─ [P0] Planner 代理 - 任务规划
│   ├─ [P0] Reviewer 代理 - 代码审查
│   └─ [P0] TDD 代理 - 测试驱动
│
└─ Day 5: Bot 集成
    ├─ [P0] /agent <name> <task> 命令
    └─ [P0] 代理结果格式化

Week 3 任务:
├─ Day 1-2: 更多代理
│   ├─ [P1] Architect 代理 - 系统设计
│   ├─ [P1] Debugger 代理 - 调试专家
│   └─ [P1] DocWriter 代理 - 文档编写
│
├─ Day 3-4: 代理编排
│   ├─ [P1] 多代理协作流程
│   └─ [P1] /orchestrate 命令
│
└─ Day 5: 测试 & 文档
    └─ 代理使用文档
```

**目录结构**:
```
src/
├─ agents/
│   ├─ __init__.py
│   ├─ base.py              # Agent 基类
│   ├─ registry.py          # 注册中心
│   └─ builtin/
│       ├─ planner.py
│       ├─ reviewer.py
│       ├─ tdd.py
│       ├─ architect.py
│       ├─ debugger.py
│       └─ doc_writer.py
config/
├─ agents/
│   ├─ planner.yaml
│   ├─ reviewer.yaml
│   └─ ...
```

**代理配置示例**:
```yaml
# config/agents/planner.yaml
name: planner
description: 功能实现规划专家，分析需求并输出详细步骤
model: opus  # 复杂任务用 opus
tools:
  - Read
  - Grep
  - Glob
  - WebSearch

system_prompt: |
  你是一个功能规划专家。你的任务是:
  1. 分析用户需求，理解目标
  2. 调研现有代码结构
  3. 设计实现方案
  4. 输出详细的执行步骤

  输出格式:
  ## 需求分析
  [理解用户要什么]

  ## 现有代码分析
  [相关文件和结构]

  ## 实现方案
  [技术选型和架构]

  ## 执行步骤
  1. 第一步...
  2. 第二步...

  ## 风险提示
  [可能的问题和注意事项]
```

**交付物**:
- [x] 6 个专业子代理
- [x] `/agent` 命令
- [x] `/orchestrate` 多代理编排
- [x] 代理使用文档

**验收标准**:
- `/agent planner 实现用户认证` 输出完整规划
- `/agent reviewer` 输出代码审查报告
- 代理可自定义配置

---

### Phase 2: 记忆系统 (Week 4-5) - 核心能力

**目标**: 实现长期记忆，让 Agent 越用越聪明

```
Week 4 任务:
├─ Day 1-2: 存储层
│   ├─ [P0] LanceDB 集成
│   ├─ [P0] 记忆 Schema 设计
│   └─ [P0] Embedding 服务 (OpenAI)
│
├─ Day 3-4: 记忆管理
│   ├─ [P0] remember() - 存储记忆
│   ├─ [P0] recall() - 语义检索
│   └─ [P0] forget() - 遗忘机制
│
└─ Day 5: Bot 集成
    ├─ [P0] 自动记忆注入
    └─ [P0] /memory 命令

Week 5 任务:
├─ Day 1-2: 持续学习
│   ├─ [P1] 会话结束自动分析
│   ├─ [P1] 模式提取 (错误解决、用户纠正)
│   └─ [P1] /learn 手动学习命令
│
├─ Day 3-4: 记忆增强
│   ├─ [P1] 项目知识图谱
│   ├─ [P1] 用户偏好学习
│   └─ [P1] 记忆重要性评分
│
└─ Day 5: 优化 & 测试
    └─ 性能优化
```

**目录结构**:
```
src/
├─ memory/
│   ├─ __init__.py
│   ├─ manager.py          # 记忆管理器
│   ├─ embeddings.py       # 向量嵌入
│   ├─ learning.py         # 持续学习
│   └─ injection.py        # 记忆注入
data/
├─ memory/
│   └─ lancedb/            # 向量数据库
```

**记忆类型设计**:
```python
class MemoryType(Enum):
    # 情景记忆 - 会话相关
    SESSION_SUMMARY = "session_summary"      # 会话摘要
    ERROR_RESOLUTION = "error_resolution"    # 错误解决方案
    USER_CORRECTION = "user_correction"      # 用户纠正

    # 语义记忆 - 知识相关
    CODE_PATTERN = "code_pattern"            # 代码模式
    PROJECT_KNOWLEDGE = "project_knowledge"  # 项目知识
    USER_PREFERENCE = "user_preference"      # 用户偏好

    # 技能记忆 - 学习相关
    LEARNED_SKILL = "learned_skill"          # 学习到的技能
    WORKAROUND = "workaround"                # 变通方案
```

**交付物**:
- [x] LanceDB 记忆存储
- [x] 语义检索 (recall)
- [x] 自动记忆注入
- [x] `/memory` 管理命令
- [x] `/learn` 学习命令
- [x] 持续学习系统

**验收标准**:
- 相关记忆自动注入到 prompt
- `/memory search 认证` 返回相关记忆
- 会话结束后自动提取模式
- 记忆跨会话持久化

---

### Phase 3: MCP 工具生态 (Week 6) - 能力扩展

**目标**: 集成 MCP 协议，扩展工具能力

```
Week 6 任务:
├─ Day 1-2: MCP 框架
│   ├─ [P1] MCP Server 管理器
│   ├─ [P1] 工具发现与注册
│   └─ [P1] 配置文件解析
│
├─ Day 3-4: 核心 MCP 集成
│   ├─ [P1] GitHub MCP (PR, Issues)
│   ├─ [P1] Memory MCP (持久记忆)
│   └─ [P1] Trading MCP (Freqtrade)
│
└─ Day 5: 自定义 MCP
    ├─ [P1] 创建 Trading MCP Server
    └─ [P1] MCP 使用文档
```

**MCP 配置**:
```json
// config/mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "trading": {
      "command": "python",
      "args": ["-m", "src.mcp.trading"],
      "description": "Freqtrade 交易操作"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

**自定义 Trading MCP**:
```python
# src/mcp/trading.py
from mcp.server import Server
from mcp.types import Tool

server = Server("trading")

@server.tool()
async def backtest_strategy(
    strategy_name: str,
    timerange: str = "20250101-20260101",
    timeframe: str = "1h"
) -> dict:
    """回测交易策略"""
    # 调用 Freqtrade API
    ...

@server.tool()
async def upload_strategy(strategy_code: str, name: str) -> dict:
    """上传策略到 Railway"""
    # Base64 编码上传
    ...

@server.tool()
async def get_trading_status() -> dict:
    """获取交易状态"""
    ...
```

**交付物**:
- [x] MCP 管理器
- [x] GitHub MCP 集成
- [x] Trading MCP Server
- [x] `/mcp` 管理命令

---

### Phase 4: 桌面端开发 (Week 7-9) - 完整体验

**目标**: 开发桌面端应用，提供精美 UI

```
Week 7 任务:
├─ Day 1-2: 项目初始化
│   ├─ [P2] Tauri 2 + React 19 项目
│   ├─ [P2] Tailwind CSS 4 + shadcn/ui
│   └─ [P2] 项目结构搭建
│
├─ Day 3-4: 核心界面
│   ├─ [P2] 会话列表
│   ├─ [P2] 聊天界面
│   └─ [P2] 消息渲染 (Markdown)
│
└─ Day 5: 本地 Agent
    └─ [P2] Claude Agent SDK 集成

Week 8 任务:
├─ Day 1-2: 增强功能
│   ├─ [P2] 代理面板
│   ├─ [P2] 记忆面板
│   └─ [P2] 工具面板
│
├─ Day 3-4: Artifact 预览
│   ├─ [P2] 代码预览 (语法高亮)
│   ├─ [P2] HTML 预览 (iframe)
│   └─ [P2] Markdown 预览
│
└─ Day 5: 设置界面
    └─ [P2] API 配置、代理配置

Week 9 任务:
├─ Day 1-2: 同步系统
│   ├─ [P2] WebSocket 连接
│   ├─ [P2] 记忆同步
│   └─ [P2] 会话同步
│
├─ Day 3-4: 双模式
│   ├─ [P2] Local/Cloud 切换
│   └─ [P2] 离线支持
│
└─ Day 5: 打包发布
    ├─ [P2] macOS 打包
    ├─ [P2] Windows 打包
    └─ [P2] Linux 打包
```

**桌面端技术栈**:
```
desktop/
├─ src/                      # React 前端
│   ├─ components/
│   │   ├─ chat/             # 聊天组件
│   │   ├─ agents/           # 代理面板
│   │   ├─ memory/           # 记忆面板
│   │   └─ artifacts/        # 预览组件
│   ├─ hooks/
│   ├─ stores/               # Zustand 状态
│   └─ App.tsx
├─ src-tauri/                # Rust 后端
│   ├─ src/
│   │   ├─ main.rs
│   │   ├─ agent.rs          # Agent 接口
│   │   └─ sync.rs           # 同步逻辑
│   └─ Cargo.toml
└─ package.json
```

**交付物**:
- [x] 桌面端应用 (macOS/Windows/Linux)
- [x] 本地 Agent 执行
- [x] 记忆/会话同步
- [x] Artifact 预览

---

### Phase 5: 高级功能 (Week 10) - 完善体验

**目标**: 完善细节，提升体验

```
Week 10 任务:
├─ Day 1-2: Hook 系统
│   ├─ [P1] PreToolUse Hook
│   ├─ [P1] PostToolUse Hook
│   └─ [P1] 自动 lint/type 检查
│
├─ Day 3-4: 体验优化
│   ├─ [P1] 快捷键支持
│   ├─ [P1] 主题切换
│   └─ [P1] 通知系统
│
└─ Day 5: 发布
    ├─ 完整文档
    ├─ 发布公告
    └─ 用户指南
```

---

## 三、详细任务分解

### 3.1 Week 1: 快速增强

#### Task 1.1: 消息节流器
```python
# src/bot/services/stream_throttle.py

class StreamThrottler:
    """消息编辑节流器 - 借鉴 ClawdBot"""

    def __init__(self, throttle_ms: int = 300):
        self.throttle_ms = throttle_ms
        self.last_update = 0
        self.pending_text = ""
        self.message = None

    async def update(self, text: str):
        """节流更新"""
        now = time.time() * 1000
        self.pending_text = text

        if now - self.last_update >= self.throttle_ms:
            await self._flush()

    async def _flush(self):
        """刷新到 Telegram"""
        if self.pending_text and self.message:
            try:
                await self.message.edit_text(
                    self.pending_text,
                    parse_mode="Markdown"
                )
                self.last_update = time.time() * 1000
            except Exception:
                pass  # 忽略编辑错误

    async def finish(self):
        """确保最后内容发送"""
        await self._flush()
```

#### Task 1.2: 工具详情格式化
```python
# src/bot/services/tool_formatter.py

class ToolFormatter:
    """工具调用详情格式化 - 借鉴 ClawdBot"""

    TOOL_ICONS = {
        "Read": "📖",
        "Write": "✏️",
        "Edit": "🔧",
        "Bash": "💻",
        "Grep": "🔍",
        "Glob": "📂",
        "WebFetch": "🌐",
        "WebSearch": "🔎",
        "Task": "📋",
    }

    def format(self, tool_name: str, tool_input: dict) -> str:
        """格式化工具调用"""
        icon = self.TOOL_ICONS.get(tool_name, "🔧")

        if tool_name == "Read":
            path = tool_input.get("file_path", "")
            return f"{icon} Read → `{self._short_path(path)}`"

        elif tool_name == "Edit":
            path = tool_input.get("file_path", "")
            return f"{icon} Edit → `{self._short_path(path)}`"

        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")[:50]
            return f"{icon} Bash → `{cmd}`"

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"{icon} Grep → `{pattern}`"

        else:
            return f"{icon} {tool_name}"

    def _short_path(self, path: str, max_len: int = 40) -> str:
        """缩短路径显示"""
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len-3):]
```

#### Task 1.3: 安全检查
```python
# src/bot/services/safety.py

class SafetyChecker:
    """安全检查 - 借鉴 WorkAny 强制备份"""

    DANGEROUS_PATTERNS = [
        (r"rm\s+-rf", "⚠️ 危险: 递归删除，建议先备份"),
        (r"rm\s+-r", "⚠️ 危险: 递归删除，建议先备份"),
        (r"git\s+push\s+--force", "⚠️ 危险: 强制推送可能丢失历史"),
        (r"git\s+reset\s+--hard", "⚠️ 危险: 硬重置会丢失修改"),
        (r"DROP\s+TABLE", "⚠️ 危险: 删除表操作"),
        (r"DELETE\s+FROM.*WHERE\s+1", "⚠️ 危险: 可能删除所有数据"),
    ]

    BACKUP_INSTRUCTION = """
## ⚠️ 安全提醒

执行破坏性操作前，请先备份:
- 删除文件前: `cp file /workspace/backup/`
- 修改文件前: `cp file file.bak`
- 数据库操作前: 先导出备份

"""

    def check_command(self, command: str) -> Optional[str]:
        """检查命令是否危险"""
        for pattern, warning in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.I):
                return warning
        return None

    def inject_backup_instruction(self, prompt: str) -> str:
        """注入备份提醒"""
        # 检测是否包含破坏性关键词
        destructive_keywords = ["删除", "清空", "移除", "drop", "delete", "remove", "rm "]
        if any(kw in prompt.lower() for kw in destructive_keywords):
            return self.BACKUP_INSTRUCTION + prompt
        return prompt
```

#### Task 1.4: /verify 命令
```python
# src/bot/handlers/commands.py

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """运行验证循环 - 借鉴 everything-claude-code"""
    session = session_manager.get_active_session(update.effective_user.id)
    if not session or not session.project:
        await update.message.reply_text("请先选择项目: /project")
        return

    project_dir = session.project

    checks = [
        ("构建", "npm run build 2>&1 || python -m py_compile *.py 2>&1"),
        ("类型检查", "npx tsc --noEmit 2>&1 || mypy . 2>&1"),
        ("Lint", "npm run lint 2>&1 || ruff check . 2>&1"),
        ("测试", "npm test 2>&1 || pytest 2>&1"),
    ]

    status_msg = await update.message.reply_text("🔍 开始验证...")

    results = []
    for name, cmd in checks:
        try:
            result = await asyncio.create_subprocess_shell(
                cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            status = "✅" if result.returncode == 0 else "❌"
            results.append(f"{status} {name}")
        except Exception as e:
            results.append(f"⚠️ {name}: 跳过")

    report = "📋 **验证报告**\n\n" + "\n".join(results)
    await status_msg.edit_text(report, parse_mode="Markdown")
```

---

### 3.2 Week 2-3: 子代理系统

#### Task 2.1: Agent 基类
```python
# src/agents/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class AgentConfig:
    name: str
    description: str
    model: str = "sonnet"
    tools: List[str] = None
    system_prompt: str = ""

@dataclass
class AgentResult:
    success: bool
    output: str
    tool_calls: List[Dict] = None
    error: Optional[str] = None

class BaseAgent(ABC):
    """代理基类"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name

    @abstractmethod
    async def run(self, task: str, context: Dict = None) -> AgentResult:
        """执行任务"""
        pass

    def get_system_prompt(self) -> str:
        """获取系统提示"""
        return self.config.system_prompt

    def get_allowed_tools(self) -> List[str]:
        """获取允许的工具"""
        return self.config.tools or []
```

#### Task 2.2: 代理注册中心
```python
# src/agents/registry.py

import yaml
from pathlib import Path
from typing import Dict, Optional

class AgentRegistry:
    """代理注册中心"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._load_agents()
        return cls._instance

    def _load_agents(self):
        """加载所有代理配置"""
        agents_dir = Path("config/agents")
        if not agents_dir.exists():
            agents_dir.mkdir(parents=True)
            self._create_default_agents(agents_dir)

        for file in agents_dir.glob("*.yaml"):
            config = yaml.safe_load(file.read_text())
            agent_config = AgentConfig(**config)
            self._agents[config["name"]] = self._create_agent(agent_config)

    def _create_agent(self, config: AgentConfig) -> BaseAgent:
        """创建代理实例"""
        from .builtin import BUILTIN_AGENTS
        agent_class = BUILTIN_AGENTS.get(config.name, GenericAgent)
        return agent_class(config)

    def get(self, name: str) -> Optional[BaseAgent]:
        """获取代理"""
        return self._agents.get(name)

    def list(self) -> Dict[str, str]:
        """列出所有代理"""
        return {
            name: agent.config.description
            for name, agent in self._agents.items()
        }

    async def dispatch(self, name: str, task: str, context: Dict = None) -> AgentResult:
        """分发任务"""
        agent = self.get(name)
        if not agent:
            return AgentResult(
                success=False,
                output="",
                error=f"未知代理: {name}"
            )
        return await agent.run(task, context)
```

#### Task 2.3: Planner 代理
```python
# src/agents/builtin/planner.py

class PlannerAgent(BaseAgent):
    """规划代理 - 任务分解和实现规划"""

    async def run(self, task: str, context: Dict = None) -> AgentResult:
        prompt = f"""
{self.get_system_prompt()}

## 用户任务
{task}

## 项目上下文
{self._format_context(context)}

请分析任务并输出详细规划。
"""
        # 调用 Claude
        result = await self._execute_claude(prompt)
        return AgentResult(
            success=True,
            output=result,
            tool_calls=self._extract_tool_calls(result)
        )

    def _format_context(self, context: Dict) -> str:
        if not context:
            return "无"
        return f"""
- 项目目录: {context.get('project', '未指定')}
- 当前会话: {context.get('session_id', '未知')}
"""
```

---

### 3.3 Week 4-5: 记忆系统

#### Task 4.1: 记忆管理器
```python
# src/memory/manager.py

import lancedb
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4

class MemoryManager:
    """记忆管理器 - 借鉴 ClawdBot LanceDB"""

    def __init__(self, db_path: str = "data/memory/lancedb"):
        self.db = lancedb.connect(db_path)
        self._ensure_table()

    def _ensure_table(self):
        """确保表存在"""
        if "memories" not in self.db.table_names():
            self.db.create_table("memories", data=[{
                "id": "init",
                "type": "system",
                "content": "Memory system initialized",
                "embedding": [0.0] * 1536,
                "metadata": "{}",
                "created_at": datetime.now().isoformat(),
                "importance": 0.0,
                "access_count": 0,
            }])

    async def remember(
        self,
        content: str,
        memory_type: str,
        user_id: str,
        importance: float = 0.5,
        metadata: Dict = None
    ) -> str:
        """存储记忆"""
        embedding = await self._get_embedding(content)

        memory_id = str(uuid4())
        self.db.table("memories").add([{
            "id": memory_id,
            "type": memory_type,
            "content": content,
            "embedding": embedding,
            "metadata": json.dumps(metadata or {}),
            "created_at": datetime.now().isoformat(),
            "importance": importance,
            "access_count": 0,
            "user_id": user_id,
        }])

        return memory_id

    async def recall(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Dict]:
        """语义检索记忆"""
        query_embedding = await self._get_embedding(query)

        table = self.db.table("memories")
        results = table.search(query_embedding).limit(top_k * 2)

        # 过滤
        memories = []
        for r in results.to_list():
            if r["user_id"] != user_id:
                continue
            if memory_type and r["type"] != memory_type:
                continue
            memories.append(r)
            if len(memories) >= top_k:
                break

        # 更新访问计数
        for m in memories:
            self._increment_access(m["id"])

        return memories

    async def forget(
        self,
        memory_id: Optional[str] = None,
        older_than_days: int = None,
        low_importance: bool = False
    ):
        """遗忘记忆"""
        table = self.db.table("memories")

        if memory_id:
            table.delete(f"id = '{memory_id}'")
        elif older_than_days:
            cutoff = datetime.now() - timedelta(days=older_than_days)
            if low_importance:
                table.delete(
                    f"created_at < '{cutoff.isoformat()}' "
                    f"AND importance < 0.3 AND access_count < 3"
                )
            else:
                table.delete(f"created_at < '{cutoff.isoformat()}'")

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
```

#### Task 4.2: 记忆注入
```python
# src/memory/injection.py

class MemoryInjector:
    """记忆注入器 - 将相关记忆注入 prompt"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def inject(
        self,
        prompt: str,
        user_id: str,
        project: Optional[str] = None
    ) -> str:
        """注入相关记忆"""
        # 检索相关记忆
        memories = await self.memory.recall(
            query=prompt,
            user_id=user_id,
            top_k=5
        )

        if not memories:
            return prompt

        # 格式化记忆
        memory_text = self._format_memories(memories)

        # 注入到 prompt
        enhanced = f"""
## 相关记忆 (自动注入)

{memory_text}

---

## 用户请求

{prompt}
"""
        return enhanced

    def _format_memories(self, memories: List[Dict]) -> str:
        """格式化记忆列表"""
        lines = []
        for i, m in enumerate(memories, 1):
            type_icon = {
                "error_resolution": "🔧",
                "user_correction": "📝",
                "code_pattern": "💡",
                "project_knowledge": "📚",
            }.get(m["type"], "💭")

            lines.append(f"{i}. {type_icon} [{m['type']}] {m['content'][:100]}...")

        return "\n".join(lines)
```

---

## 四、里程碑与验收

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| **M0** | Week 1 | 消息体验优化 | 消息不闪烁，工具有详情 |
| **M1** | Week 3 | 子代理系统 | 6 个代理可用 |
| **M2** | Week 5 | 记忆系统 | 跨会话记忆生效 |
| **M3** | Week 6 | MCP 集成 | GitHub/Trading MCP 可用 |
| **M4** | Week 9 | 桌面端 | 可打包安装使用 |
| **M5** | Week 10 | v2.0 发布 | 全功能可用 |

---

## 五、技术风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| LanceDB 性能 | 中 | 中 | 备选 ChromaDB |
| Tauri 兼容性 | 中 | 高 | 先支持 macOS，渐进式 |
| 同步冲突 | 高 | 中 | 简化策略，last-write-wins |
| Claude API 成本 | 中 | 中 | Embedding 用 OpenAI |
| 记忆数据量 | 低 | 中 | 遗忘机制 + 压缩 |

---

## 六、资源需求

### 6.1 依赖更新

```txt
# requirements.txt 新增

# Memory
lancedb>=0.4.0
openai>=1.0.0

# MCP
mcp>=0.1.0

# Utils
pyyaml>=6.0
websockets>=12.0
```

### 6.2 目录结构

```
cloudwork/
├─ src/
│   ├─ bot/                  # 现有 Bot
│   ├─ agents/               # [新] 子代理
│   ├─ memory/               # [新] 记忆系统
│   ├─ mcp/                  # [新] MCP 集成
│   └─ sync/                 # [新] 同步服务
├─ desktop/                  # [新] 桌面端
│   ├─ src/
│   └─ src-tauri/
├─ config/
│   ├─ agents/               # [新] 代理配置
│   ├─ skills/               # [新] 技能配置
│   └─ mcp.json              # [新] MCP 配置
└─ data/
    └─ memory/               # [新] 记忆数据
```

---

## 七、开发优先级总结

### 立即开始 (Week 1)
1. ✅ 消息节流 - 10 分钟搞定，体验提升明显
2. ✅ 工具详情 - 30 分钟，信息密度提升
3. ✅ /verify - 1 小时，开发效率提升

### 核心价值 (Week 2-5)
1. ⭐ 子代理系统 - 核心能力，提升效率
2. ⭐ 记忆系统 - 核心能力，越用越强

### 能力扩展 (Week 6)
1. 🔧 MCP 集成 - 工具生态

### 完整体验 (Week 7-10)
1. 🖥️ 桌面端 - 精美体验
2. 🔄 同步系统 - 无缝切换

---

**文档版本**: v1.0
**更新日期**: 2026-01-25
**作者**: CloudWork Team
