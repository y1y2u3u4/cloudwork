# CloudWork → Agent Platform Upgrade Plan

> **Target**: Upgrade CloudWork to an OpenAI Frontier-level Agent management platform
> **Duration**: 12 weeks (6 phases)
> **Status**: Phase 1 - Not Started
> **Created**: 2026-02-08
> **Last Updated**: 2026-02-08

---

## Overview

Transform CloudWork from a Telegram Bot + Desktop App into a full Agent platform with:
- Agent creation & management (natural language → executable agent)
- Skills / Connections / Apps / Knowledge
- Evaluation system (accuracy, politeness, efficiency)
- Permission guardrails & approval workflows
- Operations dashboard

## Current Architecture Reusability

| Component | Reuse % | Notes |
|-----------|---------|-------|
| SessionManager (`src/bot/services/session.py`) | 95% | Session persistence logic reusable as-is |
| MemoryManager (`src/bot/services/memory.py`) | 85% | 3-layer memory → Knowledge base foundation |
| ClaudeExecutor (`src/bot/services/claude.py`) | 70% | Core engine, needs multi-LLM extension |
| TaskManager (`src/bot/services/task.py`) | 60% | Needs queue upgrade |
| SkillsManager (`src/bot/services/skills.py`) | 50% | Needs MCP refactor |
| Desktop DB (`desktop/src/shared/db/`) | 90% | SQLite + IndexedDB, extend tables |
| Desktop Settings (`desktop/src/shared/db/settings.ts`) | 80% | Already has AIProvider/MCPServer types |

## Key Constraints

- VPS Python 3.9 → use `from typing import Optional, List, Dict, Tuple`
- Syncthing sync mechanism unchanged
- Telegram Bot retained as mobile entry point
- Desktop App as primary management UI

---

## Phase 1: Agent Registry + LLM Router (Week 1-2)

**Goal**: Establish Agent data model and multi-LLM abstraction layer

### Backend Tasks

- [ ] **1.1** Create `src/core/` directory structure
  ```
  src/core/
  ├── __init__.py
  ├── models/
  │   ├── agent.py        # Agent data model
  │   ├── skill.py        # Skill data model
  │   └── knowledge.py    # Knowledge data model
  ├── llm/
  │   ├── router.py       # LLM Router (multi-model dispatch)
  │   ├── providers/
  │   │   ├── claude_cli.py    # Refactored ClaudeExecutor
  │   │   ├── claude_api.py    # Anthropic API direct
  │   │   └── openai.py        # OpenAI compatible
  │   └── base.py         # LLMProvider abstract base
  └── registry/
      ├── agent_registry.py   # Agent CRUD
      └── storage.py          # SQLite persistence
  ```

- [ ] **1.2** Define Agent data model
  ```python
  @dataclass
  class AgentConfig:
      id: str
      name: str
      description: str           # Natural language description
      system_prompt: str          # Generated/manual system prompt
      model: str                  # Default model (sonnet/opus/gpt-4o)
      provider: str               # claude-cli / claude-api / openai
      skills: List[str]           # Associated skill IDs
      knowledge_ids: List[str]    # Associated knowledge IDs
      permissions: Dict           # Permission config
      metadata: Dict              # Extension fields
      created_at: str
      updated_at: str
      status: str                 # active / paused / archived
  ```

- [ ] **1.3** Implement LLM Router
  - Unified interface: `async def execute(prompt, agent_config, context) -> AsyncIterator[Event]`
  - Extract CLI execution logic from existing `ClaudeExecutor`
  - Routing: `agent_config.provider` → corresponding Provider

- [ ] **1.4** Create SQLite schema
  ```sql
  CREATE TABLE agents (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      system_prompt TEXT,
      model TEXT DEFAULT 'sonnet',
      provider TEXT DEFAULT 'claude-cli',
      skills TEXT DEFAULT '[]',
      knowledge_ids TEXT DEFAULT '[]',
      permissions TEXT DEFAULT '{}',
      metadata TEXT DEFAULT '{}',
      status TEXT DEFAULT 'active',
      created_at TEXT,
      updated_at TEXT
  );
  ```

- [ ] **1.5** Add `aiosqlite` dependency to `requirements.txt`

### Frontend Tasks

- [ ] **1.6** Agent list page (card view: name/description/status/model)
- [ ] **1.7** Agent creation wizard (natural language → auto-generate system prompt)
- [ ] **1.8** Agent detail/edit page

### API Tasks

- [ ] **1.9** Desktop API endpoints
  ```
  POST   /api/agents           # Create Agent
  GET    /api/agents           # List
  GET    /api/agents/{id}      # Detail
  PUT    /api/agents/{id}      # Update
  DELETE /api/agents/{id}      # Delete
  POST   /api/agents/{id}/run  # Run with specified Agent
  ```

### Telegram Bot Tasks

- [ ] **1.10** `/agents` command — list all Agents
- [ ] **1.11** `/agent <name> <prompt>` — execute with specified Agent

### Verification

- [ ] Agent CRUD via Desktop API works
- [ ] Agent execution via LLM Router works
- [ ] Telegram `/agents` and `/agent` commands functional
- [ ] Existing Bot functionality unaffected

---

## Phase 2: Knowledge Base + Context Injection (Week 3-4)

**Goal**: Knowledge management with auto context injection during Agent execution

### Backend Tasks

- [ ] **2.1** Knowledge data models (`KnowledgeCollection`, `Document`)
- [ ] **2.2** BM25 search engine (pure Python, no extra deps)
  - Document chunking: paragraph/heading split, 500-1000 tokens per chunk
  - Top-k results injected into system prompt
- [ ] **2.3** Context injection pipeline
  ```
  User prompt → Extract keywords → BM25 search → Concat context → Send to LLM
  ```
- [ ] **2.4** File upload support (.txt, .md, .pdf text extraction)
  - Storage: `data/knowledge/{collection_id}/`
- [ ] **2.5** SQLite tables: `knowledge_collections`, `knowledge_documents`

### Frontend Tasks

- [ ] **2.6** Knowledge collection list/create/delete page
- [ ] **2.7** Document upload/preview/delete
- [ ] **2.8** Agent settings: associate knowledge bases

### API Tasks

- [ ] **2.9** Knowledge API endpoints
  ```
  POST   /api/knowledge                          # Create collection
  GET    /api/knowledge                           # List
  POST   /api/knowledge/{id}/documents            # Upload document
  DELETE /api/knowledge/{id}/documents/{doc_id}   # Delete document
  GET    /api/knowledge/{id}/search?q=...         # Search
  ```

### Verification

- [ ] Documents uploadable and searchable
- [ ] Agent execution includes relevant knowledge context
- [ ] Search returns relevant results for test queries

---

## Phase 3: Permission Guardrails + Audit (Week 5-6)

**Goal**: Permission control and operation auditing

### Backend Tasks

- [ ] **3.1** Permission engine (`PermissionRule`, `PermissionEngine`)
  - Rule types: `allow` / `deny` / `require_approval`
  - Resources: `file_write` / `shell_exec` / `api_call` / `*`
  - Priority: DENY > REQUIRE_APPROVAL > ALLOW
- [ ] **3.2** Approval workflow
  - Pause Agent on `require_approval`
  - Telegram push: inline keyboard (Approve / Deny)
  - Desktop UI: approval queue
  - Configurable timeout auto-deny
- [ ] **3.3** Audit log table
  ```sql
  CREATE TABLE audit_logs (
      id TEXT PRIMARY KEY,
      agent_id TEXT,
      session_id TEXT,
      action TEXT,
      resource TEXT,
      status TEXT,
      details TEXT,
      user_id TEXT,
      timestamp TEXT
  );
  ```
- [ ] **3.4** Sandbox enhancement
  - Agent-level filesystem isolation (workspace subdirectory)
  - Command whitelist/blacklist
- [ ] **3.5** SQLite tables: `permission_rules`, `audit_logs`

### Frontend Tasks

- [ ] **3.6** Permission config UI (Agent detail → Permissions Tab)
  - Rule CRUD, preset templates: "Read-only" / "Development" / "Full Access"
- [ ] **3.7** Approval queue page (pending list, detail, batch operations)

### Verification

- [ ] Denied actions are blocked
- [ ] Approval requests appear in Telegram and Desktop
- [ ] Audit logs record all actions
- [ ] Approval flow completes end-to-end

---

## Phase 4: Skills System + MCP Integration (Week 7-8)

**Goal**: Refactor Skills into composable packages, integrate MCP

### Backend Tasks

- [ ] **4.1** Skill data model (types: `prompt` / `mcp` / `code`)
- [ ] **4.2** MCP Server Manager
  - Lifecycle management (start/stop/health check)
  - Tool discovery & registration
  - Dynamic loading during Agent execution
- [ ] **4.3** Skill execution engine
  ```python
  class SkillExecutor:
      async def execute(self, skill, inputs, agent_context) -> Dict:
          # Routes to prompt/mcp/code executor
  ```
- [ ] **4.4** Migrate built-in skills
  - PlanningManager → `skill_planning.yaml`
  - RalphLoopManager → `skill_ralph.yaml`
  - KeywordMiningManager → `skill_seo.yaml`
  - Memory → `skill_memory.yaml`
- [ ] **4.5** SQLite tables: `skills`, `agent_skills`, `mcp_servers`

### Frontend Tasks

- [ ] **4.6** Skill marketplace (built-in + custom)
- [ ] **4.7** Skill creation wizard
- [ ] **4.8** Agent detail → Skills Tab (associate/disassociate)
- [ ] **4.9** MCP management page (server status, tool browser)

### Verification

- [ ] Skills discoverable and executable
- [ ] MCP servers manageable via UI
- [ ] Agent can use associated skills during execution
- [ ] Existing skills migrated and functional

---

## Phase 5: Evaluation System (Week 9-10)

**Goal**: Agent quality evaluation

### Backend Tasks

- [ ] **5.1** Evaluation data models (`EvaluationRun`, `TestCase`)
- [ ] **5.2** Evaluation engine
  - LLM-as-Judge: Claude/GPT evaluates Agent output quality
  - Metrics: Accuracy, Politeness, Efficiency, Task Completion
  - Test set management: manual + extract from history
- [ ] **5.3** Auto evaluation pipeline
  ```
  Trigger → Load test set → Execute Agent per case → Collect output → LLM scoring → Aggregate → Report
  ```
- [ ] **5.4** SQLite tables: `evaluation_runs`, `test_cases`

### Frontend Tasks

- [ ] **5.5** Evaluation dashboard
  - Agent score card (radar chart: accuracy/politeness/efficiency/completion)
  - Historical trend chart
  - Test set management
  - Evaluation run trigger/view

### Verification

- [ ] Evaluation runs complete successfully
- [ ] Metrics displayed correctly in dashboard
- [ ] Historical trends tracked

---

## Phase 6: Operations Dashboard + Task Queue (Week 11-12)

**Goal**: Operations monitoring and multi-task parallel execution

### Backend Tasks

- [ ] **6.1** Task queue upgrade
  - Single task → parallel queue (`max_concurrent_tasks`)
  - Task priority & state machine: pending → running → completed/failed/cancelled
  - Queue persistence to SQLite
- [ ] **6.2** Operations metrics collection
  ```python
  @dataclass
  class AgentStats:
      agent_id: str
      total_runs: int
      successful_runs: int
      failed_runs: int
      avg_duration: float
      avg_tokens: int
      success_rate: float
      last_run_at: str
  ```
- [ ] **6.3** Real-time monitoring (WebSocket push)
- [ ] **6.4** SQLite tables: `task_queue`, `agent_stats`

### Frontend Tasks

- [ ] **6.5** Operations dashboard
  - Overview: active agents / today's tasks / success rate / avg duration
  - Agent list: status / last run / success rate
  - Task timeline
  - Audit log browser
- [ ] **6.6** Inbox / Cases (Frontier-style)
  - Pending items from Agent execution
  - Approval requests
  - Exception alerts
  - Batch operations

### Verification

- [ ] Multiple tasks run in parallel
- [ ] Dashboard shows real-time metrics
- [ ] Inbox aggregates all pending items

---

## Database Schema Summary

New tables on top of existing Desktop SQLite:

| Phase | Tables |
|-------|--------|
| 1 | `agents` |
| 2 | `knowledge_collections`, `knowledge_documents` |
| 3 | `permission_rules`, `audit_logs` |
| 4 | `skills`, `agent_skills`, `mcp_servers` |
| 5 | `evaluation_runs`, `test_cases` |
| 6 | `task_queue`, `agent_stats` |

## New Dependencies

| Dependency | Purpose | Phase |
|-----------|---------|-------|
| `aiosqlite` | Async SQLite | 1 |
| `rank-bm25` | Text search | 2 |
| `pyyaml` (existing) | Skill definitions | 4 |

## Migration Strategy

1. **Incremental**: Each phase independently deliverable, no breaking changes
2. **Dual entry**: Telegram Bot + Desktop App share `src/core/` layer
3. **Data compatible**: Existing sessions.json unchanged, new data in SQLite
4. **Feature flags**: New features controlled via config toggles

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Python 3.9 compatibility | All new code uses `typing` module |
| SQLite concurrent writes | WAL mode + write queue |
| MCP Server stability | Health checks + auto-restart |
| Evaluation cost (LLM calls) | Configurable frequency, offline eval support |
| Frontend workload | Prioritize Desktop UI, Telegram core features only |

---

## Progress Tracking

| Phase | Status | Start | End | Notes |
|-------|--------|-------|-----|-------|
| Phase 1: Agent Registry + LLM Router | Not Started | - | - | |
| Phase 2: Knowledge Base + Context Injection | Not Started | - | - | |
| Phase 3: Permission Guardrails + Audit | Not Started | - | - | |
| Phase 4: Skills System + MCP Integration | Not Started | - | - | |
| Phase 5: Evaluation System | Not Started | - | - | |
| Phase 6: Operations Dashboard + Task Queue | Not Started | - | - | |

---

*Related docs:*
- `docs/openai-frontier-research.md` — Frontier platform research
- `docs/cloudwork-v3-iteration-plan.md` — Previous v3 plan
- `docs/cloudwork-v2-plan.md` — v2 plan
