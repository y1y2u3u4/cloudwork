# CloudWork v2: 超级 Agent 实施计划

> 目标：将 CloudWork 打造成**云端 + 桌面端**双模式的超级 Agent
> 借鉴：ClawdBot (记忆系统、工具能力) + everything-claude-code (子代理、持续学习)

---

## 一、整体架构设计

### 1.1 双端架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CloudWork v2 Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐              ┌──────────────────────┐         │
│  │    Desktop Client    │◄────────────►│    Cloud Server      │         │
│  │    (Tauri + React)   │   WebSocket  │    (VPS)             │         │
│  │                      │   + Sync     │                      │         │
│  │  ┌────────────────┐  │              │  ┌────────────────┐  │         │
│  │  │ Local Agent    │  │              │  │ Remote Agent   │  │         │
│  │  │ (Claude SDK)   │  │              │  │ (Claude CLI)   │  │         │
│  │  └────────────────┘  │              │  └────────────────┘  │         │
│  │  ┌────────────────┐  │              │  ┌────────────────┐  │         │
│  │  │ Local Memory   │◄─┼──── Sync ───►│  │ Cloud Memory   │  │         │
│  │  │ (LanceDB)      │  │              │  │ (LanceDB)      │  │         │
│  │  └────────────────┘  │              │  └────────────────┘  │         │
│  │  ┌────────────────┐  │              │  ┌────────────────┐  │         │
│  │  │ Local Skills   │◄─┼──── Sync ───►│  │ Cloud Skills   │  │         │
│  │  │ & Agents       │  │              │  │ & Agents       │  │         │
│  │  └────────────────┘  │              │  └────────────────┘  │         │
│  └──────────────────────┘              └──────────────────────┘         │
│              │                                    │                      │
│              ▼                                    ▼                      │
│       ┌────────────┐                      ┌────────────┐                │
│       │  Telegram  │                      │  Telegram  │                │
│       │  (可选)    │                      │  Bot       │                │
│       └────────────┘                      └────────────┘                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心模块

| 模块 | 功能 | 技术选型 |
|------|------|----------|
| **桌面端** | 本地 Agent + 可视化 | Tauri 2 + React + Tailwind |
| **云端** | 远程执行 + Telegram Bot | Python + Claude CLI |
| **记忆系统** | 长期记忆 + 语义检索 | LanceDB + OpenAI Embeddings |
| **技能系统** | 子代理 + 持续学习 | Markdown 配置 + 动态加载 |
| **同步层** | 双端数据同步 | WebSocket + CRDT |
| **MCP 集成** | 工具能力扩展 | MCP 协议 + 插件系统 |

---

## 二、记忆系统设计

### 2.1 三层记忆架构

借鉴 ClawdBot 的 LanceDB 记忆系统 + everything-claude-code 的持续学习：

```
记忆层级:
├── 工作记忆 (Working Memory)
│   ├─ 当前会话上下文
│   ├─ 最近工具调用历史
│   └─ 临时任务状态
│
├── 情景记忆 (Episodic Memory)
│   ├─ 会话摘要 (自动提取)
│   ├─ 重要对话片段
│   ├─ 用户纠正记录
│   └─ 错误解决方案
│
└── 语义记忆 (Semantic Memory)
    ├─ 学习到的技能模式
    ├─ 项目知识图谱
    ├─ 用户偏好设置
    └─ 代码库理解
```

### 2.2 记忆存储结构

```python
# data/memory/schema.py

class MemoryEntry:
    """记忆条目"""
    id: str                    # UUID
    type: str                  # "episodic" | "semantic" | "skill"
    content: str               # 记忆内容
    embedding: List[float]     # 向量嵌入 (1536 维)
    metadata: Dict             # 元数据
    created_at: datetime
    updated_at: datetime
    access_count: int          # 访问次数 (用于遗忘)
    importance: float          # 重要性评分 (0-1)
    source: str                # "auto" | "user" | "system"
    tags: List[str]            # 标签

class MemoryMetadata:
    """记忆元数据"""
    session_id: Optional[str]
    project: Optional[str]
    user_id: str
    context: str               # 触发上下文
    related_files: List[str]   # 相关文件
```

### 2.3 记忆操作

```python
# src/memory/manager.py

class MemoryManager:
    """记忆管理器"""

    def __init__(self, db_path: str):
        self.db = lancedb.connect(db_path)
        self.embedder = OpenAIEmbeddings()

    async def remember(self, content: str, memory_type: str, **metadata) -> str:
        """存储记忆"""
        embedding = await self.embedder.embed(content)
        entry = MemoryEntry(
            id=str(uuid4()),
            type=memory_type,
            content=content,
            embedding=embedding,
            metadata=metadata,
            importance=self._calculate_importance(content, metadata),
        )
        self.db.table("memories").add([entry.dict()])
        return entry.id

    async def recall(self, query: str, top_k: int = 5, filters: Dict = None) -> List[MemoryEntry]:
        """语义检索记忆"""
        query_embedding = await self.embedder.embed(query)
        results = self.db.table("memories").search(query_embedding).limit(top_k)

        if filters:
            results = results.where(self._build_filter(filters))

        return [MemoryEntry(**r) for r in results.to_list()]

    async def forget(self, memory_id: str = None, older_than: datetime = None):
        """遗忘机制"""
        if memory_id:
            self.db.table("memories").delete(f"id = '{memory_id}'")
        elif older_than:
            # 遗忘旧的、低重要性、少访问的记忆
            self.db.table("memories").delete(
                f"updated_at < '{older_than}' AND importance < 0.3 AND access_count < 3"
            )

    async def consolidate(self):
        """记忆整合 (将相似记忆合并)"""
        # 定期运行，合并相似的情景记忆为语义记忆
        pass
```

### 2.4 持续学习系统

借鉴 everything-claude-code 的自动模式提取：

```python
# src/memory/learning.py

class ContinuousLearning:
    """持续学习系统"""

    PATTERNS_TO_DETECT = [
        "error_resolution",      # 错误解决方案
        "user_corrections",      # 用户纠正
        "workarounds",           # 变通方案
        "debugging_techniques",  # 调试技巧
        "project_specific",      # 项目特定模式
        "code_patterns",         # 代码模式
    ]

    async def analyze_session(self, session: Session) -> List[LearnedPattern]:
        """会话结束时分析并提取模式"""
        if session.message_count < 10:
            return []

        # 使用 Claude 分析会话，提取可学习的模式
        prompt = f"""
        分析以下会话，提取可复用的模式：

        会话内容:
        {session.get_transcript()}

        请识别:
        1. 错误解决方案 - 如何解决了某个错误
        2. 用户纠正 - 用户纠正了 AI 的什么理解
        3. 变通方案 - 绕过某个问题的技巧
        4. 调试技巧 - 有效的调试方法
        5. 项目特定 - 该项目的特殊约定

        输出格式:
        ```json
        [
          {{
            "type": "error_resolution",
            "pattern": "模式描述",
            "context": "适用场景",
            "solution": "解决方案",
            "example": "示例代码"
          }}
        ]
        ```
        """

        patterns = await self.claude.analyze(prompt)
        return [self._create_learned_pattern(p) for p in patterns]

    async def on_user_correction(self, original: str, correction: str):
        """用户纠正时立即学习"""
        pattern = LearnedPattern(
            type="user_correction",
            pattern=f"用户偏好: {correction}",
            context=original,
            importance=0.9,  # 用户纠正优先级高
        )
        await self.memory.remember(
            content=pattern.to_markdown(),
            memory_type="semantic",
            source="user",
        )
```

### 2.5 记忆注入

```python
# src/memory/injection.py

class MemoryInjector:
    """将相关记忆注入到 prompt 中"""

    async def inject(self, prompt: str, context: Dict) -> str:
        """根据当前上下文注入相关记忆"""

        # 1. 检索相关记忆
        relevant_memories = await self.memory.recall(
            query=prompt,
            top_k=5,
            filters={
                "user_id": context["user_id"],
                "project": context.get("project"),
            }
        )

        # 2. 检索相关技能
        relevant_skills = await self.skill_manager.match(prompt)

        # 3. 构建增强 prompt
        enhanced_prompt = f"""
## 相关记忆 (自动注入)
{self._format_memories(relevant_memories)}

## 已学习的模式
{self._format_skills(relevant_skills)}

## 用户请求
{prompt}
"""
        return enhanced_prompt
```

---

## 三、工具能力系统

### 3.1 工具架构

```
工具层级:
├── 内置工具 (Built-in)
│   ├─ 文件操作: Read, Write, Edit, Glob, Grep
│   ├─ 系统操作: Bash, Task
│   └─ 网络操作: WebFetch, WebSearch
│
├── MCP 工具 (Model Context Protocol)
│   ├─ 官方 MCP: GitHub, Supabase, Vercel, Railway
│   ├─ 社区 MCP: Firecrawl, ClickHouse, Memory
│   └─ 自定义 MCP: Trading, Monitoring
│
├── 专业子代理 (Specialized Agents)
│   ├─ Planner: 任务规划
│   ├─ Architect: 系统设计
│   ├─ CodeReviewer: 代码审查
│   ├─ TDDGuide: 测试驱动开发
│   ├─ Debugger: 调试专家
│   └─ DocWriter: 文档编写
│
└── 自定义技能 (Custom Skills)
    ├─ 领域知识: Trading, DevOps
    ├─ 项目技能: 项目特定模式
    └─ 学习技能: 从会话中提取
```

### 3.2 子代理系统

借鉴 everything-claude-code 的 9 个专业子代理：

```yaml
# config/agents/planner.yaml
name: planner
description: 功能实现规划专家
model: opus
tools:
  - Read
  - Grep
  - Glob
  - WebSearch

system_prompt: |
  你是一个功能规划专家。你的任务是:
  1. 分析用户需求
  2. 调研现有代码结构
  3. 设计实现方案
  4. 输出详细的步骤计划

  输出格式:
  ## 需求分析
  ...
  ## 现有代码分析
  ...
  ## 实现方案
  ...
  ## 执行步骤
  1. ...
  2. ...
```

```python
# src/agents/registry.py

class AgentRegistry:
    """子代理注册中心"""

    BUILT_IN_AGENTS = {
        "planner": PlannerAgent,
        "architect": ArchitectAgent,
        "code-reviewer": CodeReviewerAgent,
        "security-reviewer": SecurityReviewerAgent,
        "tdd-guide": TDDGuideAgent,
        "debugger": DebuggerAgent,
        "doc-writer": DocWriterAgent,
        "refactor": RefactorAgent,
        "e2e-runner": E2ERunnerAgent,
    }

    def __init__(self):
        self.agents = {}
        self._load_builtin()
        self._load_custom()

    def _load_custom(self):
        """从 config/agents/ 加载自定义代理"""
        agents_dir = Path("config/agents")
        for file in agents_dir.glob("*.yaml"):
            config = yaml.safe_load(file.read_text())
            self.agents[config["name"]] = CustomAgent(config)

    async def dispatch(self, agent_name: str, task: str) -> AgentResult:
        """分发任务到指定代理"""
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_name}")
        return await agent.run(task)
```

### 3.3 MCP 集成

```python
# src/mcp/manager.py

class MCPManager:
    """MCP 服务器管理"""

    def __init__(self, config_path: str = "config/mcp.json"):
        self.config = json.load(open(config_path))
        self.servers = {}

    async def start_server(self, name: str):
        """启动 MCP 服务器"""
        config = self.config["mcpServers"].get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        server = MCPServer(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", {}),
        )
        await server.start()
        self.servers[name] = server

    def get_tools(self, server_name: str) -> List[Tool]:
        """获取 MCP 服务器提供的工具"""
        return self.servers[server_name].list_tools()

    async def call_tool(self, server_name: str, tool_name: str, args: Dict) -> Any:
        """调用 MCP 工具"""
        return await self.servers[server_name].call_tool(tool_name, args)
```

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
      "args": ["-m", "src.mcp.trading_server"],
      "env": {
        "FREQTRADE_API_URL": "${FREQTRADE_API_URL}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-filesystem", "/workspace"]
    }
  }
}
```

### 3.4 自定义技能系统

```markdown
<!-- config/skills/trading/freqtrade-backtest.md -->
---
name: freqtrade-backtest
description: Freqtrade 策略回测技能
triggers:
  - "回测"
  - "backtest"
  - "测试策略"
tools:
  - Bash
  - WebFetch
---

# Freqtrade 策略回测

## 操作步骤

1. **上传策略到 Railway**
   ```bash
   B64=$(cat {strategy_file} | base64 -w0)
   ~/bin/railway ssh --service freqtrade --project {project_id} \
     "echo '$B64' | base64 -d > /freqtrade/user_data/strategies/{strategy_name}.py"
   ```

2. **验证策略语法**
   ```bash
   ~/bin/railway ssh --service freqtrade --project {project_id} \
     "python3 -c \"from {strategy_name} import {strategy_name}; print('OK')\""
   ```

3. **执行回测**
   ```bash
   curl -X POST -H "Authorization: Bearer {token}" \
     "{api_url}/api/v1/backtest" \
     -d '{"strategy": "{strategy_name}", "timeframe": "1h", "timerange": "{timerange}"}'
   ```

4. **获取结果**
   ```bash
   curl -H "Authorization: Bearer {token}" "{api_url}/api/v1/backtest"
   ```
```

---

## 四、本地-云端同步系统

### 4.1 同步架构

```
同步数据:
├── 记忆数据 (Memory)
│   ├─ LanceDB 向量数据
│   └─ 记忆元数据
│
├── 技能配置 (Skills)
│   ├─ agents/*.yaml
│   ├─ skills/**/*.md
│   └─ commands/*.md
│
├── 会话数据 (Sessions)
│   ├─ sessions.json
│   └─ session_transcripts/
│
└── 用户设置 (Settings)
    ├─ preferences.json
    └─ mcp.json
```

### 4.2 同步协议

```python
# src/sync/protocol.py

class SyncProtocol:
    """CRDT-based 同步协议"""

    async def sync(self, local_state: State, remote_state: State) -> State:
        """合并本地和远程状态"""
        # 使用 CRDT (Conflict-free Replicated Data Type) 处理冲突
        merged = self.crdt_merge(local_state, remote_state)
        return merged

    def crdt_merge(self, local: State, remote: State) -> State:
        """CRDT 合并策略"""
        merged = State()

        # 1. 记忆合并: 使用时间戳，保留最新
        for memory_id in set(local.memories.keys()) | set(remote.memories.keys()):
            local_mem = local.memories.get(memory_id)
            remote_mem = remote.memories.get(memory_id)

            if not local_mem:
                merged.memories[memory_id] = remote_mem
            elif not remote_mem:
                merged.memories[memory_id] = local_mem
            else:
                # 保留更新时间更晚的
                merged.memories[memory_id] = (
                    local_mem if local_mem.updated_at > remote_mem.updated_at
                    else remote_mem
                )

        # 2. 技能合并: 使用版本号
        # 3. 会话合并: 追加模式
        # ...

        return merged
```

### 4.3 WebSocket 实时同步

```python
# src/sync/websocket.py

class SyncServer:
    """云端同步服务器"""

    def __init__(self):
        self.clients: Dict[str, WebSocket] = {}

    async def handle_connection(self, websocket: WebSocket, user_id: str):
        """处理客户端连接"""
        self.clients[user_id] = websocket

        try:
            async for message in websocket:
                data = json.loads(message)

                if data["type"] == "sync_request":
                    # 客户端请求同步
                    await self.handle_sync(user_id, data)

                elif data["type"] == "push":
                    # 客户端推送变更
                    await self.handle_push(user_id, data)

        finally:
            del self.clients[user_id]

    async def broadcast_change(self, user_id: str, change: Dict):
        """广播变更到所有客户端"""
        if user_id in self.clients:
            await self.clients[user_id].send(json.dumps({
                "type": "change",
                "data": change,
            }))
```

```python
# src/sync/client.py (桌面端)

class SyncClient:
    """桌面端同步客户端"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.ws = None
        self.local_state = LocalState()

    async def connect(self):
        """连接到云端"""
        self.ws = await websockets.connect(self.server_url)
        asyncio.create_task(self.listen())

    async def listen(self):
        """监听服务器推送"""
        async for message in self.ws:
            data = json.loads(message)
            if data["type"] == "change":
                await self.apply_remote_change(data["data"])

    async def push_change(self, change: Dict):
        """推送本地变更"""
        await self.ws.send(json.dumps({
            "type": "push",
            "data": change,
        }))

    async def full_sync(self):
        """全量同步"""
        await self.ws.send(json.dumps({
            "type": "sync_request",
            "local_state": self.local_state.to_dict(),
        }))
```

---

## 五、桌面端设计

### 5.1 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| **框架** | Tauri 2 | Rust 后端，轻量级 |
| **前端** | React 19 + TypeScript | 现代前端 |
| **UI** | Tailwind CSS 4 + shadcn/ui | 美观易用 |
| **状态** | Zustand | 轻量状态管理 |
| **本地 DB** | SQLite + LanceDB | 会话 + 向量 |

### 5.2 界面设计

```
┌─────────────────────────────────────────────────────────────────┐
│  CloudWork Desktop                                    ─ □ ×     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────────────────────────────────────┐ │
│  │ Sessions    │  │ Chat Area                                 │ │
│  │             │  │                                           │ │
│  │ ▶ Current   │  │ 👤 帮我分析这个策略的回测结果              │ │
│  │   Session   │  │                                           │ │
│  │             │  │ 🤖 我来分析回测结果...                     │ │
│  │ ▷ 重构认证  │  │                                           │ │
│  │ ▷ Trading   │  │ 📊 [回测结果预览]                         │ │
│  │ ▷ Cron 任务 │  │    ├─ 总收益: +15.3%                      │ │
│  │             │  │    ├─ 最大回撤: -8.2%                     │ │
│  ├─────────────┤  │    └─ 胜率: 62%                          │ │
│  │ Agents      │  │                                           │ │
│  │             │  │ [Tool] Bash: 获取回测 API 结果             │ │
│  │ 🧠 Planner  │  │ [Tool] Read: 分析策略代码                  │ │
│  │ 🔍 Reviewer │  │                                           │ │
│  │ 🧪 TDD      │  ├───────────────────────────────────────────┤ │
│  │ 📝 Docs     │  │ ┌─────────────────────────────────────┐   │ │
│  │             │  │ │ 输入消息... (Ctrl+Enter 发送)       │   │ │
│  ├─────────────┤  │ └─────────────────────────────────────┘   │ │
│  │ Memory      │  │ [📎] [🎤] [📷]          [Local] [Cloud]   │ │
│  │             │  └───────────────────────────────────────────┘ │
│  │ 📌 5 条相关 │  ┌───────────────────────────────────────────┐ │
│  │ 💡 3 个技能 │  │ Artifact Preview                          │ │
│  │             │  │                                           │ │
│  ├─────────────┤  │ [Chart] 收益曲线图                        │ │
│  │ Sync Status │  │                                           │ │
│  │ ✅ 已同步   │  │                                           │ │
│  └─────────────┘  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 核心功能

1. **双模式执行**
   - Local: 本地 Claude Agent SDK 执行
   - Cloud: 远程 VPS 执行 (适合长时间任务)

2. **记忆面板**
   - 显示当前相关记忆
   - 手动添加/删除记忆
   - 记忆搜索

3. **代理面板**
   - 快速切换专业代理
   - 自定义代理配置

4. **同步状态**
   - 实时显示同步状态
   - 冲突解决界面

---

## 六、实施路线图

### Phase 1: 基础架构 (2 周)

```
Week 1:
├─ Day 1-2: 记忆系统核心
│   ├─ LanceDB 集成
│   ├─ 基础 CRUD 操作
│   └─ Embedding 服务
│
├─ Day 3-4: 技能系统
│   ├─ Markdown 解析
│   ├─ 技能加载器
│   └─ 技能匹配
│
└─ Day 5-7: 子代理框架
    ├─ Agent 基类
    ├─ 内置代理实现
    └─ 代理调度器

Week 2:
├─ Day 1-3: 云端 Bot 增强
│   ├─ 记忆注入
│   ├─ 技能调用
│   └─ 子代理命令
│
└─ Day 4-7: 测试 & 文档
    ├─ 单元测试
    ├─ 集成测试
    └─ 使用文档
```

### Phase 2: 桌面端开发 (3 周)

```
Week 3:
├─ Day 1-2: Tauri 项目初始化
├─ Day 3-4: 基础 UI 框架
└─ Day 5-7: 会话界面

Week 4:
├─ Day 1-3: 本地 Agent 集成
├─ Day 4-5: 记忆面板
└─ Day 6-7: 代理面板

Week 5:
├─ Day 1-3: Artifact 预览
├─ Day 4-5: 设置界面
└─ Day 6-7: 打包 & 测试
```

### Phase 3: 同步系统 (2 周)

```
Week 6:
├─ Day 1-2: 同步协议设计
├─ Day 3-4: 云端同步服务
└─ Day 5-7: 桌面端同步客户端

Week 7:
├─ Day 1-3: 冲突解决
├─ Day 4-5: 离线支持
└─ Day 6-7: 测试 & 优化
```

### Phase 4: 高级功能 (2 周)

```
Week 8:
├─ Day 1-3: 持续学习系统
├─ Day 4-5: MCP 集成
└─ Day 6-7: Trading MCP

Week 9:
├─ Day 1-3: Hook 系统
├─ Day 4-5: 验证循环
└─ Day 6-7: 发布 & 文档
```

---

## 七、技术细节

### 7.1 目录结构

```
cloudwork/
├── src/
│   ├── bot/                    # Telegram Bot (现有)
│   │   ├── handlers/
│   │   └── services/
│   ├── memory/                 # 记忆系统 (新增)
│   │   ├── manager.py
│   │   ├── learning.py
│   │   └── injection.py
│   ├── agents/                 # 子代理系统 (新增)
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── builtin/
│   ├── skills/                 # 技能系统 (新增)
│   │   ├── loader.py
│   │   └── matcher.py
│   ├── mcp/                    # MCP 集成 (新增)
│   │   ├── manager.py
│   │   └── trading_server.py
│   └── sync/                   # 同步系统 (新增)
│       ├── server.py
│       └── protocol.py
├── desktop/                    # 桌面端 (新增)
│   ├── src/                    # React 前端
│   ├── src-tauri/              # Tauri 后端
│   └── package.json
├── config/
│   ├── agents/                 # 代理配置
│   ├── skills/                 # 技能配置
│   ├── mcp.json                # MCP 配置
│   └── .env
├── data/
│   ├── memory/                 # LanceDB 数据
│   ├── sessions/               # 会话数据
│   └── sync/                   # 同步状态
└── docs/
    ├── cloudwork-v2-plan.md    # 本文档
    └── api/                    # API 文档
```

### 7.2 依赖更新

```txt
# requirements.txt (新增)

# Memory
lancedb>=0.4.0
openai>=1.0.0  # for embeddings

# Sync
websockets>=12.0
python-crdt>=0.1.0

# MCP
mcp>=0.1.0

# Utils
pyyaml>=6.0
```

### 7.3 配置示例

```json
// config/cloudwork.json
{
  "memory": {
    "db_path": "data/memory",
    "embedding_model": "text-embedding-3-small",
    "auto_capture": true,
    "auto_recall": true,
    "recall_top_k": 5
  },
  "agents": {
    "default": "planner",
    "model_override": {
      "planner": "opus",
      "code-reviewer": "sonnet"
    }
  },
  "sync": {
    "enabled": true,
    "server_url": "wss://your-vps:8765",
    "auto_sync": true,
    "sync_interval": 60
  },
  "learning": {
    "auto_extract": true,
    "min_session_length": 10,
    "patterns": ["error_resolution", "user_corrections", "workarounds"]
  }
}
```

---

## 八、关键里程碑

| 里程碑 | 目标 | 预计时间 |
|--------|------|----------|
| **M1** | 记忆系统上线 (Telegram Bot) | Week 2 |
| **M2** | 子代理系统可用 | Week 2 |
| **M3** | 桌面端 Alpha 版本 | Week 5 |
| **M4** | 本地-云端同步可用 | Week 7 |
| **M5** | 持续学习系统上线 | Week 8 |
| **M6** | v2.0 正式发布 | Week 9 |

---

## 九、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| LanceDB 性能问题 | 中 | 预留 ChromaDB 作为备选 |
| Tauri 兼容性 | 中 | 优先支持 macOS/Linux，Windows 后续 |
| 同步冲突复杂 | 高 | 简化初版策略，后续迭代 |
| 记忆数据量大 | 中 | 实现遗忘机制和压缩 |
| Claude API 成本 | 中 | Embedding 使用 OpenAI，Claude 仅核心对话 |

---

## 十、总结

CloudWork v2 将实现:

1. **超强记忆** - LanceDB 向量记忆 + 持续学习
2. **专业代理** - 9+ 专业子代理
3. **丰富工具** - MCP 生态 + 自定义技能
4. **双端体验** - 桌面级 UI + 远程 Telegram
5. **无缝同步** - CRDT 实时同步

最终目标: **一个既能随时随地远程使用，又有桌面级体验的超级 AI 编程助手**
