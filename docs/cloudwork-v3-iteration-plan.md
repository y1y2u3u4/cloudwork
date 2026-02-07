# CloudWork v3 完整迭代计划

> **目标**: 对标 OpenAI Frontier，打造企业级 AI Agent 平台
> **周期**: 8 周 (2 个月)
> **原则**: 增量交付、每周可用、向后兼容

---

## 一、版本定位

### 1.1 演进路线

```
CloudWork v1 (当前)     → v2 (体验优化)      → v3 (Frontier 级别)
─────────────────────────────────────────────────────────────────
单任务串行执行           任务队列+并发        多 Agent 协作
会话级隔离               项目级知识           组织级知识库
硬编码权限               配置化权限           细粒度权限边界
技能硬编码               技能插件化           MCP 工具生态
Telegram only           +本地节点            多渠道接入
```

### 1.2 与 OpenAI Frontier 对标

| Frontier 特性 | CloudWork v3 对应 | 优先级 |
|--------------|-------------------|--------|
| 共享上下文 (Shared Context) | 组织级知识库 | P0 |
| 权限边界 (Clear Permissions) | 权限边界系统 | P1 |
| 工具执行环境 (Agent Execution) | 多 Agent 协作框架 | P0 |
| 企业集成 (Enterprise Integration) | 多渠道接入 | P2 |
| 反馈学习 (Feedback Loop) | 持续学习引擎 | P1 |

---

## 二、8 周迭代计划

### Sprint 1: 任务队列 + 并发控制 (Week 1-2)

**目标**: 支持多任务并行执行，解决当前最大痛点

#### Week 1: 基础设施

| 任务 | 文件 | 描述 |
|------|------|------|
| 任务队列设计 | `src/bot/services/queue.py` | asyncio.PriorityQueue 实现 |
| 并发控制器 | `src/bot/services/concurrency.py` | 每用户最多 3 个并发任务 |
| 任务状态机 | `src/bot/services/task_state.py` | pending → running → completed/failed |
| 任务持久化 | `data/tasks.json` | 重启后恢复未完成任务 |

```python
# src/bot/services/queue.py
class TaskQueue:
    """优先级任务队列"""

    def __init__(self, max_concurrent_per_user: int = 3):
        self.queue = asyncio.PriorityQueue()
        self.running: Dict[str, List[Task]] = {}  # user_id -> tasks
        self.max_concurrent = max_concurrent_per_user
        self.workers: List[asyncio.Task] = []

    async def submit(self, task: Task, priority: int = 0) -> str:
        """提交任务，返回任务 ID"""
        task.id = str(uuid4())
        task.status = TaskStatus.PENDING
        task.priority = priority
        task.created_at = datetime.now()

        await self.queue.put((priority, task))
        self._persist()
        return task.id

    async def start_workers(self, num_workers: int = 5):
        """启动后台 worker"""
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

    async def _worker(self, worker_id: int):
        """Worker 消费任务"""
        while True:
            priority, task = await self.queue.get()

            # 检查用户并发限制
            user_running = len(self.running.get(task.user_id, []))
            if user_running >= self.max_concurrent:
                # 放回队列，稍后重试
                await self.queue.put((priority, task))
                await asyncio.sleep(1)
                continue

            # 执行任务
            self._add_running(task)
            try:
                task.status = TaskStatus.RUNNING
                result = await self._execute(task)
                task.status = TaskStatus.COMPLETED
                task.result = result
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
            finally:
                self._remove_running(task)
                self._persist()
```

#### Week 2: Bot 集成

| 任务 | 文件 | 描述 |
|------|------|------|
| /queue 命令 | `handlers/commands.py` | 查看任务队列状态 |
| /cancel 增强 | `handlers/commands.py` | 取消指定任务 |
| 任务完成通知 | `services/notification.py` | 长任务完成后主动通知 |
| 优先级支持 | `handlers/messages.py` | `!urgent` 前缀提升优先级 |

**交付物**:
- [x] 任务队列系统
- [x] 并发控制 (每用户 3 个)
- [x] `/queue` 查看任务状态
- [x] 长任务完成通知

**验收标准**:
- 可同时提交多个任务
- 任务按优先级执行
- 用户可查看所有任务状态
- Bot 重启后任务不丢失

---

### Sprint 2: 组织级知识库 (Week 3-4)

**目标**: Agent 具备跨会话的组织记忆

#### Week 3: 向量存储

| 任务 | 文件 | 描述 |
|------|------|------|
| LanceDB 集成 | `src/memory/storage.py` | 向量数据库 |
| Embedding 服务 | `src/memory/embedding.py` | OpenAI text-embedding-3-small |
| 记忆 Schema | `src/memory/schema.py` | 统一记忆数据结构 |
| 迁移工具 | `scripts/migrate_memory.py` | JSON → LanceDB |

```python
# src/memory/schema.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List

class MemoryType(Enum):
    # 情景记忆
    SESSION_SUMMARY = "session_summary"
    ERROR_RESOLUTION = "error_resolution"
    USER_CORRECTION = "user_correction"

    # 语义记忆
    PROJECT_KNOWLEDGE = "project_knowledge"
    CODE_PATTERN = "code_pattern"
    API_USAGE = "api_usage"

    # 组织记忆 (新增)
    ORG_RULE = "org_rule"           # 组织规则
    BEST_PRACTICE = "best_practice" # 最佳实践
    DOMAIN_KNOWLEDGE = "domain"     # 领域知识

@dataclass
class Memory:
    id: str
    type: MemoryType
    content: str
    embedding: List[float]

    # 元数据
    user_id: str
    project: Optional[str] = None
    session_id: Optional[str] = None

    # 时间戳
    created_at: str
    updated_at: str
    last_accessed: str

    # 权重
    importance: float = 0.5
    access_count: int = 0
    decay_factor: float = 1.0

    # 关联
    related_memories: List[str] = None
    tags: List[str] = None
    metadata: Dict = None
```

#### Week 4: 知识注入

| 任务 | 文件 | 描述 |
|------|------|------|
| 上下文注入器 | `src/memory/injector.py` | 自动注入相关记忆 |
| 记忆检索 API | `src/memory/retrieval.py` | 语义检索 + 重排序 |
| /memory 命令 | `handlers/commands.py` | search/add/forget |
| 自动学习 | `src/memory/learner.py` | 会话结束自动提取 |

```python
# src/memory/injector.py
class ContextInjector:
    """上下文注入器 - 对标 Frontier 的 Shared Context"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.max_tokens = 2000  # 注入记忆的最大 token

    async def inject(
        self,
        prompt: str,
        user_id: str,
        project: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """注入相关上下文"""

        # 1. 检索相关记忆
        memories = await self.memory.recall(
            query=prompt,
            user_id=user_id,
            top_k=10
        )

        # 2. 加载项目规则
        project_rules = await self._load_project_rules(project)

        # 3. 加载组织知识
        org_knowledge = await self._load_org_knowledge(user_id)

        # 4. 构建上下文
        context = self._build_context(
            memories=memories,
            project_rules=project_rules,
            org_knowledge=org_knowledge
        )

        # 5. 注入到 prompt
        if context:
            return f"""## 相关上下文 (自动注入)

{context}

---

## 用户请求

{prompt}"""

        return prompt

    def _build_context(self, memories, project_rules, org_knowledge) -> str:
        """构建上下文，控制在 token 限制内"""
        sections = []

        if org_knowledge:
            sections.append(f"### 组织知识\n{org_knowledge}")

        if project_rules:
            sections.append(f"### 项目规则\n{project_rules}")

        if memories:
            memory_text = "\n".join([
                f"- [{m['type']}] {m['content'][:100]}..."
                for m in memories[:5]
            ])
            sections.append(f"### 相关记忆\n{memory_text}")

        return "\n\n".join(sections)
```

**交付物**:
- [x] LanceDB 向量存储
- [x] 语义检索 + 重排序
- [x] 自动上下文注入
- [x] `/memory` 管理命令
- [x] 会话结束自动学习

**验收标准**:
- 相关记忆自动注入到每个请求
- `/memory search 认证` 返回相关记忆
- 跨会话记忆持久化
- 支持组织级知识（所有用户共享）

---

### Sprint 3: 多 Agent 协作框架 (Week 5-6)

**目标**: 复杂任务分解执行

#### Week 5: Agent 框架

| 任务 | 文件 | 描述 |
|------|------|------|
| Agent 基类 | `src/agents/base.py` | 定义 Agent 接口 |
| Agent 注册中心 | `src/agents/registry.py` | 动态注册 Agent |
| 内置 Agent | `src/agents/builtin/` | 6 个专业 Agent |
| Agent 配置 | `config/agents/*.yaml` | YAML 配置 Agent |

```python
# src/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class AgentCapability:
    """Agent 能力声明"""
    name: str
    description: str
    input_schema: Dict
    output_schema: Dict

@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str
    artifacts: List[Dict] = None  # 生成的文件/代码
    tool_calls: List[Dict] = None
    sub_results: List['AgentResult'] = None  # 子 Agent 结果
    error: Optional[str] = None
    metadata: Dict = None

class BaseAgent(ABC):
    """Agent 基类 - 对标 Frontier 的 Agent Execution"""

    def __init__(self, config: Dict):
        self.name = config.get('name', self.__class__.__name__)
        self.description = config.get('description', '')
        self.model = config.get('model', 'sonnet')
        self.tools = config.get('tools', [])
        self.system_prompt = config.get('system_prompt', '')
        self.max_iterations = config.get('max_iterations', 10)

    @abstractmethod
    async def run(self, task: str, context: Dict = None) -> AgentResult:
        """执行任务"""
        pass

    def get_capabilities(self) -> List[AgentCapability]:
        """声明能力"""
        return []

    async def delegate(self, agent_name: str, subtask: str) -> AgentResult:
        """委托给其他 Agent"""
        from .registry import AgentRegistry
        registry = AgentRegistry()
        agent = registry.get(agent_name)
        if not agent:
            return AgentResult(success=False, output="", error=f"Agent {agent_name} not found")
        return await agent.run(subtask)
```

```yaml
# config/agents/planner.yaml
name: planner
description: 任务规划专家，分析需求并输出详细步骤
model: opus
tools:
  - Read
  - Grep
  - Glob
  - WebSearch

system_prompt: |
  你是一个任务规划专家。你的职责是：
  1. 分析用户需求，理解目标
  2. 调研现有代码结构
  3. 设计实现方案
  4. 输出详细的执行步骤

  输出格式：
  ## 需求分析
  [理解用户要什么]

  ## 代码分析
  [相关文件和结构]

  ## 实现方案
  [技术选型和架构]

  ## 执行步骤
  1. 第一步...
  2. 第二步...

  ## 风险提示
  [可能的问题]

capabilities:
  - name: plan_feature
    description: 规划功能实现
  - name: analyze_codebase
    description: 分析代码库结构
```

#### Week 6: 编排系统

| 任务 | 文件 | 描述 |
|------|------|------|
| 任务分解器 | `src/agents/decomposer.py` | 将复杂任务拆分 |
| Agent 编排器 | `src/agents/orchestrator.py` | 多 Agent 协作 |
| 结果聚合器 | `src/agents/aggregator.py` | 合并多个 Agent 结果 |
| /agent 命令 | `handlers/commands.py` | 调用指定 Agent |

```python
# src/agents/orchestrator.py
class AgentOrchestrator:
    """Agent 编排器 - 多 Agent 协作"""

    def __init__(self):
        self.registry = AgentRegistry()
        self.decomposer = TaskDecomposer()
        self.aggregator = ResultAggregator()
        self.max_parallel = 3

    async def execute(self, task: str, context: Dict = None) -> AgentResult:
        """执行复杂任务"""

        # 1. 分解任务
        subtasks = await self.decomposer.decompose(task, context)

        if len(subtasks) == 1:
            # 简单任务，直接执行
            return await self._execute_single(subtasks[0], context)

        # 2. 构建执行计划
        plan = self._build_execution_plan(subtasks)

        # 3. 按依赖顺序执行
        results = []
        for stage in plan.stages:
            # 同一阶段的任务可并行
            stage_results = await asyncio.gather(*[
                self._execute_single(subtask, context)
                for subtask in stage.tasks
            ])
            results.extend(stage_results)

            # 检查是否需要中止
            if any(not r.success for r in stage_results):
                break

        # 4. 聚合结果
        return self.aggregator.aggregate(results)

    async def _execute_single(self, subtask: SubTask, context: Dict) -> AgentResult:
        """执行单个子任务"""
        agent = self.registry.get(subtask.agent_name)
        if not agent:
            return AgentResult(
                success=False,
                output="",
                error=f"Agent {subtask.agent_name} not found"
            )

        return await agent.run(subtask.description, context)
```

**内置 Agent**:

| Agent | 职责 | 模型 |
|-------|------|------|
| `planner` | 任务规划 | opus |
| `coder` | 代码实现 | sonnet |
| `reviewer` | 代码审查 | sonnet |
| `tester` | 测试编写 | sonnet |
| `debugger` | 问题调试 | opus |
| `documenter` | 文档编写 | haiku |

**交付物**:
- [x] Agent 框架 + 注册中心
- [x] 6 个内置 Agent
- [x] 任务分解器
- [x] Agent 编排器
- [x] `/agent` 命令

**验收标准**:
- `/agent planner 实现用户认证` 输出规划
- 复杂任务自动分解给多个 Agent
- Agent 可相互委托任务

---

### Sprint 4: 权限边界 + 工具插件化 (Week 7-8)

**目标**: 安全可控的执行环境 + 可扩展的工具生态

#### Week 7: 权限边界系统

| 任务 | 文件 | 描述 |
|------|------|------|
| 权限规则引擎 | `src/security/permissions.py` | 定义权限规则 |
| 操作审计日志 | `src/security/audit.py` | 记录所有操作 |
| 危险操作拦截 | `src/security/interceptor.py` | 拦截危险命令 |
| 二次确认机制 | `src/security/confirmation.py` | 敏感操作确认 |

```python
# src/security/permissions.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import fnmatch
import re

class PermissionLevel(Enum):
    ALLOW = "allow"           # 允许
    CONFIRM = "confirm"       # 需确认
    DENY = "deny"             # 拒绝
    AUDIT = "audit"           # 允许但审计

@dataclass
class PermissionRule:
    """权限规则"""
    action: str               # 操作类型: file_read, file_write, bash, git_push...
    pattern: str              # 匹配模式: /workspace/**, rm -rf *, ...
    level: PermissionLevel
    reason: Optional[str] = None

class PermissionChecker:
    """权限检查器 - 对标 Frontier 的 Clear Permissions"""

    def __init__(self, rules_path: str = "config/permissions.yaml"):
        self.rules = self._load_rules(rules_path)
        self.audit_log = AuditLog()

    def check(self, action: str, target: str, user_id: str) -> PermissionResult:
        """检查操作权限"""

        # 查找匹配规则
        for rule in self.rules:
            if rule.action != action:
                continue
            if not self._match_pattern(rule.pattern, target):
                continue

            # 记录审计日志
            if rule.level in [PermissionLevel.AUDIT, PermissionLevel.CONFIRM]:
                self.audit_log.log(action, target, user_id, rule.level.value)

            return PermissionResult(
                allowed=rule.level != PermissionLevel.DENY,
                requires_confirmation=rule.level == PermissionLevel.CONFIRM,
                reason=rule.reason
            )

        # 默认允许
        return PermissionResult(allowed=True)

    def _match_pattern(self, pattern: str, target: str) -> bool:
        """匹配模式"""
        # 支持 glob 和正则
        if pattern.startswith("regex:"):
            return bool(re.match(pattern[6:], target))
        return fnmatch.fnmatch(target, pattern)

# config/permissions.yaml
PERMISSION_RULES = """
rules:
  # 文件操作
  - action: file_read
    pattern: "/workspace/**"
    level: allow

  - action: file_read
    pattern: "/etc/passwd"
    level: deny
    reason: 系统敏感文件

  - action: file_write
    pattern: "/workspace/**"
    level: allow

  - action: file_write
    pattern: "**/.env*"
    level: confirm
    reason: 环境变量文件可能包含密钥

  # Bash 操作
  - action: bash
    pattern: "regex:rm\\s+-rf\\s+/"
    level: deny
    reason: 禁止删除根目录

  - action: bash
    pattern: "regex:rm\\s+-rf"
    level: confirm
    reason: 递归删除需确认

  - action: bash
    pattern: "regex:git\\s+push\\s+--force"
    level: confirm
    reason: 强制推送可能丢失历史

  - action: bash
    pattern: "regex:sudo\\s+"
    level: deny
    reason: 禁止 sudo 操作

  # Git 操作
  - action: git_push
    pattern: "main"
    level: confirm
    reason: 推送到主分支需确认

  - action: git_push
    pattern: "*"
    level: audit
"""
```

#### Week 8: 工具插件化

| 任务 | 文件 | 描述 |
|------|------|------|
| 技能加载器 | `src/skills/loader.py` | 动态加载 .skill 文件 |
| 技能注册表 | `src/skills/registry.py` | 管理所有技能 |
| 技能组合器 | `src/skills/composer.py` | 组合多个技能 |
| /skills 命令 | `handlers/commands.py` | 列出/调用技能 |

```python
# src/skills/loader.py
from pathlib import Path
from typing import Dict, List
import yaml

@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    version: str
    author: str

    # 执行配置
    prompt_template: str
    model: str = "sonnet"
    tools: List[str] = None

    # 参数定义
    parameters: List[Dict] = None

    # 钩子
    pre_hooks: List[str] = None
    post_hooks: List[str] = None

class SkillLoader:
    """技能加载器"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self._load_all()

    def _load_all(self):
        """加载所有技能"""
        for skill_file in self.skills_dir.rglob("*.skill"):
            skill = self._load_skill(skill_file)
            if skill:
                self.skills[skill.name] = skill

    def _load_skill(self, path: Path) -> Optional[Skill]:
        """加载单个技能"""
        try:
            content = path.read_text()
            config = yaml.safe_load(content)
            return Skill(**config)
        except Exception as e:
            print(f"Failed to load skill {path}: {e}")
            return None

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(name)

    def list(self) -> List[Dict]:
        """列出所有技能"""
        return [
            {"name": s.name, "description": s.description}
            for s in self.skills.values()
        ]

    async def execute(self, name: str, params: Dict, context: Dict) -> str:
        """执行技能"""
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Skill {name} not found")

        # 渲染 prompt
        prompt = self._render_prompt(skill.prompt_template, params)

        # 执行 pre_hooks
        for hook in skill.pre_hooks or []:
            await self._run_hook(hook, context)

        # 执行
        result = await self._execute_claude(prompt, skill.model, skill.tools)

        # 执行 post_hooks
        for hook in skill.post_hooks or []:
            await self._run_hook(hook, context)

        return result
```

```yaml
# skills/code-review.skill
name: code-review
description: 深度代码审查，检查代码质量、安全性、性能
version: "1.0.0"
author: CloudWork

model: opus

parameters:
  - name: files
    type: string
    description: 要审查的文件路径（支持 glob）
    required: true
  - name: focus
    type: string
    description: 审查重点 (security/performance/readability/all)
    default: all

prompt_template: |
  请对以下文件进行深度代码审查：

  文件: {{ files }}
  重点: {{ focus }}

  审查维度：
  1. **代码质量**: 可读性、可维护性、代码风格
  2. **安全性**: SQL注入、XSS、敏感信息泄露
  3. **性能**: 时间复杂度、内存使用、N+1 查询
  4. **最佳实践**: 设计模式、SOLID 原则

  输出格式：
  ## 审查摘要
  [总体评价]

  ## 问题列表
  | 严重程度 | 文件:行号 | 问题描述 | 建议修复 |
  |---------|----------|---------|---------|

  ## 改进建议
  [具体建议]

tools:
  - Read
  - Grep
  - Glob

post_hooks:
  - save_review_result
```

**交付物**:
- [x] 权限规则引擎
- [x] 操作审计日志
- [x] 危险操作拦截
- [x] 技能插件系统
- [x] `/skills` 命令

**验收标准**:
- `rm -rf /` 被拒绝
- `git push --force` 需二次确认
- 技能可通过 .skill 文件定义
- `/skills list` 显示所有可用技能

---

## 三、目录结构演进

```
cloudwork/
├── src/
│   ├── bot/                      # 现有 Bot (保持)
│   │   ├── handlers/
│   │   └── services/
│   │
│   ├── agents/                   # [新] 多 Agent 系统
│   │   ├── __init__.py
│   │   ├── base.py              # Agent 基类
│   │   ├── registry.py          # 注册中心
│   │   ├── orchestrator.py      # 编排器
│   │   ├── decomposer.py        # 任务分解
│   │   ├── aggregator.py        # 结果聚合
│   │   └── builtin/             # 内置 Agent
│   │       ├── planner.py
│   │       ├── coder.py
│   │       ├── reviewer.py
│   │       ├── tester.py
│   │       ├── debugger.py
│   │       └── documenter.py
│   │
│   ├── memory/                   # [新] 记忆系统
│   │   ├── __init__.py
│   │   ├── storage.py           # LanceDB 存储
│   │   ├── embedding.py         # Embedding 服务
│   │   ├── schema.py            # 记忆 Schema
│   │   ├── retrieval.py         # 检索服务
│   │   ├── injector.py          # 上下文注入
│   │   └── learner.py           # 自动学习
│   │
│   ├── security/                 # [新] 安全系统
│   │   ├── __init__.py
│   │   ├── permissions.py       # 权限规则
│   │   ├── audit.py             # 审计日志
│   │   ├── interceptor.py       # 拦截器
│   │   └── confirmation.py      # 确认机制
│   │
│   ├── skills/                   # [新] 技能系统
│   │   ├── __init__.py
│   │   ├── loader.py            # 技能加载
│   │   ├── registry.py          # 技能注册
│   │   └── composer.py          # 技能组合
│   │
│   └── queue/                    # [新] 任务队列
│       ├── __init__.py
│       ├── queue.py             # 优先级队列
│       ├── worker.py            # Worker
│       └── persistence.py       # 持久化
│
├── config/
│   ├── agents/                   # [新] Agent 配置
│   │   ├── planner.yaml
│   │   ├── coder.yaml
│   │   └── ...
│   ├── permissions.yaml          # [新] 权限规则
│   └── .env
│
├── skills/                       # [新] 技能目录
│   ├── core/
│   │   ├── planning.skill
│   │   └── ralph-loop.skill
│   ├── development/
│   │   ├── code-review.skill
│   │   ├── tdd.skill
│   │   └── refactor.skill
│   └── trading/
│       ├── backtest.skill
│       └── strategy-analyze.skill
│
├── data/
│   ├── memory/
│   │   └── lancedb/              # [新] 向量数据库
│   ├── tasks.json                # [新] 任务持久化
│   ├── audit.log                 # [新] 审计日志
│   └── sessions.json
│
└── docs/
    ├── openai-frontier-research.md
    └── cloudwork-v3-iteration-plan.md  # 本文档
```

---

## 四、依赖更新

```txt
# requirements.txt 新增

# Memory System
lancedb>=0.4.0
openai>=1.0.0           # for embeddings

# Agent System
pyyaml>=6.0

# Security
python-dateutil>=2.8.0

# Queue
aiofiles>=23.0.0
```

---

## 五、里程碑与验收

| 里程碑 | 周次 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| **M1** | Week 2 | 任务队列系统 | 多任务并行，队列持久化 |
| **M2** | Week 4 | 组织级知识库 | 语义检索，自动注入 |
| **M3** | Week 6 | 多 Agent 协作 | 任务分解，Agent 编排 |
| **M4** | Week 8 | 权限 + 技能系统 | 权限拦截，技能插件 |
| **v3.0** | Week 8 | 完整发布 | 全功能可用 |

---

## 六、技术风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| LanceDB 性能不足 | 低 | 中 | 备选 ChromaDB |
| Embedding 成本过高 | 中 | 中 | 缓存 + 本地模型备选 |
| Agent 编排复杂度 | 高 | 高 | 简化为线性执行，渐进增加 |
| 权限规则过严 | 中 | 中 | 默认宽松，可配置 |
| 技能格式不统一 | 中 | 低 | Schema 校验 |

---

## 七、后续演进 (v4+)

| 方向 | 描述 | 时间 |
|------|------|------|
| **多渠道接入** | Discord / Slack / 飞书 | v4.0 |
| **桌面端 App** | Tauri + React | v4.0 |
| **MCP 协议** | 标准化工具生态 | v4.0 |
| **Trading 深度集成** | 策略回测/优化 MCP | v4.1 |
| **团队协作** | 多用户共享 Agent | v5.0 |

---

**文档版本**: v1.0
**创建日期**: 2026-02-06
**作者**: CloudWork Team
