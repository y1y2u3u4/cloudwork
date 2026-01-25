# CloudWork 渐进式演进计划

> **核心理念**: 快速见效，架构可升级，每个组件独立演进
> **对标项目**: ClawdBot、everything-claude-code、WorkAny
> **差异定位**: 轻量部署 + Trading 专业化 + 中文优化

---

## 一、当前状态 vs 目标状态

### 1.1 能力对比矩阵

| 能力维度 | ClawdBot | everything-cc | WorkAny | CloudWork 当前 | 目标 Level |
|----------|----------|---------------|---------|----------------|------------|
| **记忆系统** | LanceDB 向量 | 持续学习 | 无 | 无 | L3 向量 |
| **多渠道入口** | 15+ 渠道 | 无 | 无 | Telegram | L2 +桌面 |
| **工具生态** | MCP + Skills | CLAUDE.md | MCP | 硬编码 | L3 MCP |
| **执行位置** | 沙箱 + 多节点 | 本地 | 本地 | VPS only | L3 多节点 |
| **桌面端** | macOS/iOS | 无 | Tauri | 无 | L2 MVP |
| **安全机制** | 审批流程 | Hook | Plan-Execute | 基础 | L2 Hook |

### 1.2 CloudWork 独特优势 (保持)

| 优势 | 描述 | 策略 |
|------|------|------|
| **轻量部署** | 单 Python 进程，systemd 管理 | 保持简单 |
| **Telegram 远程** | 随时随地，手机可用 | 核心入口 |
| **Trading 集成** | Freqtrade 深度集成 | 差异化 |
| **中文优化** | 本地化体验 | 持续优化 |

---

## 二、四级演进路线

### Level 1: 快速增强版 (1 周)

**目标**: 立即可用，体验提升 50%

```
Level 1 架构:
┌─────────────────────────────────────────┐
│              Telegram Bot                │
│                   │                      │
│         ┌────────┴────────┐              │
│         ▼                 ▼              │
│    消息节流器        工具格式化           │
│         │                 │              │
│         └────────┬────────┘              │
│                  ▼                       │
│           Claude CLI (VPS)               │
│                  │                       │
│                  ▼                       │
│         JSON 记忆存储 (本地)              │
└─────────────────────────────────────────┘
```

**交付清单**:

| 组件 | 文件 | 工作量 | 描述 |
|------|------|--------|------|
| 消息节流 | `services/throttle.py` | 30min | 300ms 节流，防闪烁 |
| 工具详情 | `services/tool_display.py` | 30min | 显示工具调用参数 |
| 智能分块 | `utils/markdown.py` | 1h | 不截断代码块 |
| JSON 记忆 | `services/memory_v1.py` | 2h | 关键词匹配 |
| /verify | `handlers/commands.py` | 1h | 构建+测试+lint |

**记忆系统 V1 设计**:

```
data/memory/
├── projects/
│   └── {project_name}.json    # 项目知识
├── errors/
│   └── {error_hash}.json      # 错误解决方案
├── corrections/
│   └── {date}.json            # 用户纠正记录
└── preferences.json           # 用户偏好
```

```python
# 记忆结构示例
# data/memory/projects/cloudwork.json
{
  "name": "cloudwork",
  "structure": {
    "entry": "src/bot/main.py",
    "handlers": "src/bot/handlers/",
    "services": "src/bot/services/"
  },
  "commands": {
    "run": "python -m src.bot.main",
    "test": "pytest tests/",
    "deploy": "systemctl restart claude-bot"
  },
  "patterns": [
    "Python 3.9 兼容，用 Optional 不用 |",
    "配置用 pydantic-settings"
  ],
  "updated_at": "2026-01-25T10:00:00Z"
}

# data/memory/errors/abc123.json
{
  "error": "ImportError: circular import",
  "context": "在 handlers 中导入 services",
  "solution": "使用延迟导入: from ..services import xxx 放在函数内",
  "project": "cloudwork",
  "created_at": "2026-01-20T15:30:00Z"
}
```

**记忆检索 V1**:

```python
# src/bot/services/memory_v1.py

class MemoryV1:
    """Level 1 记忆系统 - 关键词匹配"""

    def __init__(self, base_path: str = "data/memory"):
        self.base_path = Path(base_path)
        self._ensure_dirs()

    def recall(self, query: str, project: str = None) -> List[Dict]:
        """检索相关记忆"""
        results = []
        keywords = self._extract_keywords(query)

        # 搜索项目知识
        if project:
            proj_memory = self._load_project(project)
            if proj_memory:
                results.append({
                    "type": "project",
                    "content": proj_memory,
                    "relevance": 1.0
                })

        # 搜索错误方案
        for error_file in (self.base_path / "errors").glob("*.json"):
            error = json.loads(error_file.read_text())
            if self._match_keywords(error, keywords):
                results.append({
                    "type": "error",
                    "content": error,
                    "relevance": self._calc_relevance(error, keywords)
                })

        return sorted(results, key=lambda x: -x["relevance"])[:5]

    def remember(self, memory_type: str, content: Dict):
        """存储记忆"""
        if memory_type == "error":
            path = self.base_path / "errors" / f"{self._hash(content)}.json"
        elif memory_type == "project":
            path = self.base_path / "projects" / f"{content['name']}.json"
        elif memory_type == "correction":
            path = self.base_path / "corrections" / f"{date.today()}.json"

        # 合并或创建
        if path.exists():
            existing = json.loads(path.read_text())
            content = self._merge(existing, content)

        path.write_text(json.dumps(content, ensure_ascii=False, indent=2))

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单分词 + 停用词过滤
        words = re.findall(r'\w+', text.lower())
        stopwords = {'的', '是', '在', '了', 'the', 'a', 'is', 'in'}
        return [w for w in words if w not in stopwords and len(w) > 1]

    def _match_keywords(self, obj: Dict, keywords: List[str]) -> bool:
        """关键词匹配"""
        text = json.dumps(obj, ensure_ascii=False).lower()
        return any(kw in text for kw in keywords)
```

**Prompt 注入**:

```python
# src/bot/services/memory_injection.py

async def inject_memory(prompt: str, user_id: str, project: str = None) -> str:
    """注入相关记忆到 prompt"""
    memory = MemoryV1()
    recalls = memory.recall(prompt, project)

    if not recalls:
        return prompt

    memory_text = format_memories(recalls)

    return f"""## 相关记忆 (自动注入)

{memory_text}

---

## 用户请求

{prompt}"""
```

---

### Level 2: 增强版 (2-3 周)

**目标**: 本地云端协作，体验质变

```
Level 2 架构:
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ┌─────────────┐              ┌─────────────┐      │
│   │  Telegram   │              │   桌面端     │      │
│   │   Bot       │              │  (Tauri)    │      │
│   └──────┬──────┘              └──────┬──────┘      │
│          │                            │             │
│          └───────────┬────────────────┘             │
│                      ▼                              │
│              ┌─────────────┐                        │
│              │  Gateway    │  ← WebSocket           │
│              │  (Python)   │                        │
│              └──────┬──────┘                        │
│                     │                               │
│          ┌─────────┴─────────┐                      │
│          ▼                   ▼                      │
│   ┌─────────────┐     ┌─────────────┐              │
│   │ VPS Agent   │     │ Local Agent │              │
│   │ (Claude CLI)│     │ (Claude CLI)│              │
│   └─────────────┘     └─────────────┘              │
│          │                   │                      │
│          └─────────┬─────────┘                      │
│                    ▼                                │
│           SQLite + FTS5 记忆                         │
│           (云端存储，本地缓存)                        │
└─────────────────────────────────────────────────────┘
```

**交付清单**:

| 组件 | 描述 | 工作量 |
|------|------|--------|
| **SQLite FTS5 记忆** | 全文检索，支持模糊匹配 | 1 天 |
| **WebSocket Gateway** | 双向通信，Context 同步 | 2 天 |
| **桌面端 MVP** | Tauri + React，聊天界面 | 1 周 |
| **本地执行能力** | 桌面端内置 Claude Agent | 2 天 |
| **执行位置选择** | 本地/云端切换 | 1 天 |

**记忆系统 V2 (SQLite FTS5)**:

```python
# src/bot/services/memory_v2.py

import sqlite3
from pathlib import Path

class MemoryV2:
    """Level 2 记忆系统 - SQLite FTS5 全文检索"""

    def __init__(self, db_path: str = "data/memory/memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(
                id,
                type,           -- project/error/correction/preference
                content,        -- 主要内容
                context,        -- 上下文
                project,        -- 关联项目
                user_id,
                created_at,
                importance,
                access_count,
                tokenize='porter unicode61'  -- 支持词干匹配 + Unicode
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory_meta (
                id TEXT PRIMARY KEY,
                raw_json TEXT,  -- 原始 JSON，用于复杂查询
                embedding BLOB  -- 预留向量字段，升级 L3 时用
            )
        ''')
        conn.commit()
        conn.close()

    def remember(
        self,
        content: str,
        memory_type: str,
        user_id: str,
        project: str = None,
        context: str = None,
        importance: float = 0.5,
        metadata: Dict = None
    ) -> str:
        """存储记忆"""
        memory_id = str(uuid4())

        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO memories
            (id, type, content, context, project, user_id, created_at, importance, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (memory_id, memory_type, content, context, project, user_id,
              datetime.now().isoformat(), importance))

        # 存储原始 JSON
        conn.execute('''
            INSERT INTO memory_meta (id, raw_json) VALUES (?, ?)
        ''', (memory_id, json.dumps(metadata or {})))

        conn.commit()
        conn.close()
        return memory_id

    def recall(
        self,
        query: str,
        user_id: str,
        project: str = None,
        memory_type: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """语义检索 (FTS5 全文匹配)"""
        conn = sqlite3.connect(self.db_path)

        # 构建 FTS5 查询
        # "Python 导入错误" → "Python OR 导入 OR 错误"
        terms = self._tokenize(query)
        fts_query = " OR ".join(terms)

        sql = '''
            SELECT id, type, content, context, project, importance, access_count,
                   bm25(memories) as score
            FROM memories
            WHERE memories MATCH ? AND user_id = ?
        '''
        params = [fts_query, user_id]

        if project:
            sql += " AND project = ?"
            params.append(project)

        if memory_type:
            sql += " AND type = ?"
            params.append(memory_type)

        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        results = conn.execute(sql, params).fetchall()
        conn.close()

        # 更新访问计数
        for r in results:
            self._increment_access(r[0])

        return [
            {
                "id": r[0],
                "type": r[1],
                "content": r[2],
                "context": r[3],
                "project": r[4],
                "importance": r[5],
                "access_count": r[6],
                "score": r[7]
            }
            for r in results
        ]

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 中文分词 + 英文分词
        import jieba
        words = list(jieba.cut(text))
        # 过滤停用词和短词
        stopwords = {'的', '是', '在', '了', '和', 'the', 'a', 'is', 'in', 'to'}
        return [w for w in words if w not in stopwords and len(w) > 1]
```

**WebSocket Gateway**:

```python
# src/gateway/server.py

import asyncio
import websockets
import json
from typing import Dict, Set

class Gateway:
    """WebSocket Gateway - 连接桌面端和云端"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.memory = MemoryV2()

    async def start(self):
        """启动 Gateway"""
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # run forever

    async def handler(self, websocket, path):
        """处理连接"""
        client_id = await self._authenticate(websocket)
        if not client_id:
            return

        self.clients[client_id] = websocket
        try:
            async for message in websocket:
                await self._handle_message(client_id, json.loads(message))
        finally:
            del self.clients[client_id]

    async def _handle_message(self, client_id: str, msg: Dict):
        """处理消息"""
        action = msg.get("action")

        if action == "execute":
            # 执行任务
            result = await self._execute_task(
                msg["prompt"],
                msg.get("location", "cloud"),  # cloud or local
                msg.get("project")
            )
            await self._send(client_id, {"type": "result", "data": result})

        elif action == "sync_context":
            # 同步 Context
            context = msg.get("context", {})
            await self._broadcast_context(client_id, context)

        elif action == "recall":
            # 检索记忆
            memories = self.memory.recall(
                msg["query"],
                client_id,
                msg.get("project")
            )
            await self._send(client_id, {"type": "memories", "data": memories})

    async def _execute_task(self, prompt: str, location: str, project: str):
        """执行任务"""
        if location == "cloud":
            # VPS 执行
            return await self._execute_cloud(prompt, project)
        else:
            # 发送到桌面端执行
            return await self._request_local_execution(prompt, project)
```

**桌面端 MVP 结构**:

```
desktop/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── SessionList.tsx      # 会话列表
│   │   ├── ChatView.tsx         # 聊天界面
│   │   ├── MessageItem.tsx      # 消息组件
│   │   ├── ToolDisplay.tsx      # 工具调用显示
│   │   ├── CodeDiff.tsx         # 代码差异
│   │   └── ExecutionToggle.tsx  # 本地/云端切换
│   ├── hooks/
│   │   ├── useWebSocket.ts      # Gateway 连接
│   │   └── useMemory.ts         # 记忆操作
│   └── stores/
│       ├── sessionStore.ts
│       └── settingsStore.ts
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── agent.rs             # 本地 Agent 执行
│   │   └── commands.rs          # Tauri 命令
│   └── Cargo.toml
└── package.json
```

---

### Level 3: 完整版 (1-2 月)

**目标**: 接近 ClawdBot 能力

```
Level 3 架构:
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   入口层                                                     │
│   ├─ Telegram Bot                                           │
│   ├─ 桌面端 App                                              │
│   └─ CLI                                                    │
│                                                             │
│   Gateway 层                                                 │
│   ├─ WebSocket Server                                       │
│   ├─ MCP Manager (工具发现)                                  │
│   └─ Node Manager (设备管理)                                 │
│                                                             │
│   执行层                                                     │
│   ├─ Cloud Node (VPS)                                       │
│   ├─ Local Node (Mac/Windows)                               │
│   └─ Remote Node (其他设备)                                  │
│                                                             │
│   记忆层                                                     │
│   ├─ LanceDB 向量存储                                        │
│   ├─ 持续学习引擎                                            │
│   └─ 知识图谱                                                │
│                                                             │
│   工具层                                                     │
│   ├─ MCP Servers (GitHub/Slack/Trading...)                  │
│   └─ Custom Skills                                          │
└─────────────────────────────────────────────────────────────┘
```

**交付清单**:

| 组件 | 描述 | 工作量 |
|------|------|--------|
| **LanceDB 向量记忆** | 语义检索，真正理解意图 | 3 天 |
| **MCP 框架** | 可插拔工具生态 | 1 周 |
| **多节点执行** | 任意设备执行 | 1 周 |
| **持续学习** | 自动提取模式 | 3 天 |
| **知识图谱** | 项目关系建模 | 3 天 |

**记忆系统 V3 (LanceDB)**:

```python
# src/memory/manager.py

import lancedb
from sentence_transformers import SentenceTransformer

class MemoryV3:
    """Level 3 记忆系统 - LanceDB 向量检索"""

    def __init__(self, db_path: str = "data/memory/lancedb"):
        self.db = lancedb.connect(db_path)
        self.encoder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self._ensure_table()

    def _ensure_table(self):
        """确保表存在"""
        if "memories" not in self.db.table_names():
            self.db.create_table("memories", data=[{
                "id": "init",
                "type": "system",
                "content": "Memory system initialized",
                "vector": self.encoder.encode("init").tolist(),
                "metadata": "{}",
                "created_at": datetime.now().isoformat(),
                "importance": 0.0,
                "user_id": "system"
            }])

    async def remember(
        self,
        content: str,
        memory_type: str,
        user_id: str,
        importance: float = 0.5,
        metadata: Dict = None
    ) -> str:
        """存储记忆 (带向量)"""
        vector = self.encoder.encode(content).tolist()
        memory_id = str(uuid4())

        self.db.table("memories").add([{
            "id": memory_id,
            "type": memory_type,
            "content": content,
            "vector": vector,
            "metadata": json.dumps(metadata or {}),
            "created_at": datetime.now().isoformat(),
            "importance": importance,
            "user_id": user_id
        }])

        return memory_id

    async def recall(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        memory_type: str = None
    ) -> List[Dict]:
        """语义检索"""
        query_vector = self.encoder.encode(query).tolist()

        table = self.db.table("memories")
        results = table.search(query_vector).limit(top_k * 2).to_list()

        # 过滤
        memories = []
        for r in results:
            if r["user_id"] != user_id and r["user_id"] != "system":
                continue
            if memory_type and r["type"] != memory_type:
                continue
            memories.append(r)
            if len(memories) >= top_k:
                break

        return memories
```

**MCP 工具管理**:

```python
# src/mcp/manager.py

import subprocess
import json
from typing import Dict, List

class MCPManager:
    """MCP Server 管理器"""

    def __init__(self, config_path: str = "config/mcp.json"):
        self.config = json.loads(Path(config_path).read_text())
        self.servers: Dict[str, subprocess.Popen] = {}
        self.tools: Dict[str, Dict] = {}

    def start_all(self):
        """启动所有 MCP Server"""
        for name, config in self.config.get("servers", {}).items():
            self.start_server(name, config)

    def start_server(self, name: str, config: Dict):
        """启动单个 Server"""
        cmd = [config["command"]] + config.get("args", [])
        env = {**os.environ, **config.get("env", {})}

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env
        )
        self.servers[name] = proc

        # 发现工具
        tools = self._discover_tools(proc)
        for tool in tools:
            self.tools[f"{name}.{tool['name']}"] = tool

    def _discover_tools(self, proc) -> List[Dict]:
        """发现 Server 提供的工具"""
        # 发送 tools/list 请求
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        proc.stdin.write(json.dumps(request).encode() + b"\n")
        proc.stdin.flush()

        response = json.loads(proc.stdout.readline())
        return response.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """调用工具"""
        server_name, tool = tool_name.split(".", 1)
        proc = self.servers.get(server_name)
        if not proc:
            raise ValueError(f"Server {server_name} not running")

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
            "id": 2
        }
        proc.stdin.write(json.dumps(request).encode() + b"\n")
        proc.stdin.flush()

        response = json.loads(proc.stdout.readline())
        return response.get("result", {})
```

**MCP 配置示例**:

```json
// config/mcp.json
{
  "servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    },
    "trading": {
      "command": "python",
      "args": ["-m", "src.mcp.trading_server"],
      "description": "Freqtrade 交易 MCP Server"
    }
  }
}
```

---

### Level 4: 差异化 (持续)

**目标**: 建立独特竞争力

| 方向 | 描述 | 价值 |
|------|------|------|
| **Trading 专业化** | 回测、策略优化、风险控制 | 垂直领域深耕 |
| **中文优化** | 分词、理解、输出本地化 | 本土用户体验 |
| **轻量部署** | 单命令安装，低资源占用 | 易用性 |
| **Privacy First** | 本地优先，可选云端 | 数据安全 |

---

## 三、升级路径设计

### 3.1 记忆系统升级路径

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Level 1   │     │   Level 2   │     │   Level 3   │
│   JSON +    │ ──► │  SQLite +   │ ──► │  LanceDB +  │
│   关键词    │     │   FTS5      │     │   向量      │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
   精确匹配           模糊匹配            语义匹配
   "ImportError"    "导入错误"          "Python 引入失败"
   能找到            能找到              也能找到
```

**兼容性设计**:

```python
# src/memory/factory.py

def get_memory_manager(level: int = None) -> BaseMemory:
    """获取记忆管理器 (自动检测或指定级别)"""
    if level is None:
        level = detect_level()

    if level >= 3:
        return MemoryV3()  # LanceDB
    elif level >= 2:
        return MemoryV2()  # SQLite FTS5
    else:
        return MemoryV1()  # JSON

def detect_level() -> int:
    """检测当前安装的依赖"""
    try:
        import lancedb
        return 3
    except ImportError:
        pass

    try:
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(c)")
        return 2
    except:
        pass

    return 1
```

### 3.2 工具系统升级路径

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Level 1   │     │   Level 2   │     │   Level 3   │
│   硬编码    │ ──► │   配置化    │ ──► │    MCP     │
│   工具      │     │   工具      │     │   协议      │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
   改代码才能         改配置就能          安装即可用
   加新工具          加新工具            clawdhub install
```

### 3.3 执行系统升级路径

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Level 1   │     │   Level 2   │     │   Level 3   │
│   VPS      │ ──► │  VPS +      │ ──► │   多节点    │
│   only     │     │  本地       │     │   任意设备   │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 四、实施计划

### 4.1 Phase 1: Level 1 实现 (Week 1)

**Day 1-2: 消息体验**
- [ ] 消息节流器 (300ms)
- [ ] 工具详情格式化
- [ ] Markdown 智能分块

**Day 3-4: 记忆 V1**
- [ ] JSON 存储结构
- [ ] 关键词提取
- [ ] 记忆检索
- [ ] Prompt 注入

**Day 5: 验证命令**
- [ ] /verify 命令
- [ ] /memory 命令

### 4.2 Phase 2: Level 2 实现 (Week 2-4)

**Week 2: 记忆 V2**
- [ ] SQLite FTS5 集成
- [ ] 中文分词 (jieba)
- [ ] 迁移工具 (V1 → V2)

**Week 3: Gateway**
- [ ] WebSocket Server
- [ ] Context 同步
- [ ] 执行位置选择

**Week 4: 桌面端 MVP**
- [ ] Tauri 项目初始化
- [ ] 聊天界面
- [ ] 本地 Agent 集成

### 4.3 Phase 3: Level 3 实现 (Month 2)

**Week 5-6: 记忆 V3**
- [ ] LanceDB 集成
- [ ] Embedding 服务
- [ ] 迁移工具 (V2 → V3)

**Week 7-8: MCP**
- [ ] MCP Manager
- [ ] Trading MCP Server
- [ ] GitHub MCP 集成

**Week 9-10: 多节点**
- [ ] Node 注册发现
- [ ] 远程执行协议
- [ ] 安全认证

---

## 五、验收标准

| Level | 核心验收点 | 体验提升 |
|-------|------------|----------|
| **L1** | 消息不闪烁，记忆能检索 | 50% |
| **L2** | 本地云端可切换，桌面端可用 | 80% |
| **L3** | 语义记忆准确，MCP 工具可扩展 | 95% |
| **L4** | Trading 深度集成，中文体验优秀 | 100% |

---

## 六、技术栈总结

| 层次 | Level 1 | Level 2 | Level 3 |
|------|---------|---------|---------|
| **入口** | Telegram | +桌面端 | +CLI |
| **通信** | HTTP | WebSocket | WebSocket + gRPC |
| **记忆** | JSON | SQLite FTS5 | LanceDB |
| **工具** | 硬编码 | 配置化 | MCP |
| **执行** | VPS | +本地 | 多节点 |
| **前端** | - | Tauri + React | + 移动端 |

---

**文档版本**: v1.0
**更新日期**: 2026-01-25
**作者**: CloudWork Team
