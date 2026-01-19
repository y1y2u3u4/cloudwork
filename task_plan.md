# CloudWork 项目迁移计划

> 将 VPS Claude Code 远程执行系统改造为可复制的云端工作空间

**创建时间**: 2026-01-19
**状态**: in_progress
**参考文档**: `../../ROADMAP.md`

---

## 项目目标

将当前个人使用的 VPS Claude Code 系统改造为：
1. 可复制、可部署的开源项目
2. 支持 Docker 一键部署
3. 支持 VPS 和 Railway 云平台部署
4. 保留所有现有核心功能

**核心约束**: 在 `tasks/cloudwork/` 目录独立开发，不影响现有系统运行

---

## Phase 概览

| Phase | 名称 | 状态 | 优先级 |
|-------|------|------|--------|
| 1 | 清理与重组 | `pending` | P0 (MVP) |
| 2 | 容器化 | `pending` | P0 (MVP) |
| 3 | 云部署方案 | `pending` | P0 (MVP) |
| 4 | 配置系统重构 | `pending` | P1 |
| 5 | 代码质量提升 | `pending` | P2 |
| 6 | 安全性增强 | `pending` | P1 |
| 7 | 功能增强 | `pending` | P3 (可选) |
| 8 | 文档完善 | `pending` | P0 (MVP) |

---

## Phase 1: 清理与重组 `pending`

### 任务清单

- [ ] **1.1 创建目录结构**
  - [ ] 按 ROADMAP 中的目标结构创建目录
  - [ ] 创建 `src/bot/`, `src/utils/` 等模块目录
  - [ ] 创建占位 `__init__.py` 文件

- [ ] **1.2 创建配置模板**
  - [ ] 创建 `.env.example` 完整配置模板
  - [ ] 创建 `.gitignore`（排除敏感文件）
  - [ ] 创建 `.dockerignore`

- [ ] **1.3 创建项目基础文件**
  - [ ] 创建 `requirements.txt`
  - [ ] 创建 `CLAUDE.md`（项目说明）
  - [ ] 创建 `LICENSE` (MIT)

### 验收标准
- 目录结构完整
- 所有模板文件就位
- 可以作为独立项目 git init

---

## Phase 2: 容器化 `pending`

### 任务清单

- [ ] **2.1 编写 Dockerfile**
  - [ ] 基础镜像: Python 3.11-slim
  - [ ] 安装 Node.js 20.x (Claude CLI 依赖)
  - [ ] 安装 Claude Code CLI
  - [ ] 安装 Python 依赖

- [ ] **2.2 编写 docker-compose.yml**
  - [ ] 定义服务配置
  - [ ] 配置 Volume 持久化
  - [ ] 环境变量注入

- [ ] **2.3 持久化方案**
  - [ ] 实现 Volume 挂载方案
  - [ ] 挂载 `/app/data` (Bot 会话)
  - [ ] 挂载 `/root/.claude` (CLI 会话)

### 验收标准
- `docker build` 成功
- `docker-compose up` 可启动服务
- 重启后数据保留

---

## Phase 3: 云部署方案 `pending`

### 任务清单

- [ ] **3.1 VPS 部署脚本**
  - [ ] 创建 `scripts/setup-vps.sh`
  - [ ] 包含依赖安装、服务配置
  - [ ] 支持 Ubuntu 20.04+

- [ ] **3.2 systemd 服务配置**
  - [ ] 创建 `scripts/claude-bot.service`
  - [ ] 正确配置 EnvironmentFile

- [ ] **3.3 Railway 部署 (可选)**
  - [ ] 创建 `railway.toml`
  - [ ] 配置 Volume 挂载

### 验收标准
- VPS 一键安装脚本可用
- systemd 服务正常运行

---

## Phase 4: 配置系统重构 `pending`

### 任务清单

- [ ] **4.1 统一配置管理**
  - [ ] 使用 pydantic-settings
  - [ ] 支持 .env 和环境变量
  - [ ] 类型校验和默认值

- [ ] **4.2 配置验证**
  - [ ] 启动时验证必需配置
  - [ ] 友好的错误提示

### 验收标准
- 配置加载正常
- 缺失配置有清晰提示

---

## Phase 5: 代码质量提升 `pending`

### 任务清单

- [ ] **5.1 代码拆分**
  - [ ] `handlers/commands.py` - 命令处理
  - [ ] `handlers/messages.py` - 消息处理
  - [ ] `handlers/callbacks.py` - 回调处理
  - [ ] `services/claude.py` - Claude 执行
  - [ ] `services/session.py` - 会话管理

- [ ] **5.2 类型注解**
  - [ ] 使用 `typing` 模块 (兼容 Python 3.9)
  - [ ] 主要函数添加类型

### 验收标准
- 代码模块化清晰
- 类型检查通过

---

## Phase 6: 安全性增强 `pending`

### 任务清单

- [ ] **6.1 访问控制**
  - [ ] 用户白名单验证
  - [ ] 速率限制

- [ ] **6.2 敏感信息保护**
  - [ ] pre-commit hook
  - [ ] 完善 .gitignore

### 验收标准
- 未授权用户无法使用
- 敏感信息不会泄露

---

## Phase 7: 功能增强 `pending` (可选)

- [ ] Workspace 管理
- [ ] 文件传输
- [ ] 任务队列

---

## Phase 8: 文档完善 `pending`

### 任务清单

- [ ] **8.1 核心文档**
  - [ ] README.md (项目介绍)
  - [ ] docs/INSTALLATION.md
  - [ ] docs/CONFIGURATION.md
  - [ ] docs/COMMANDS.md

- [ ] **8.2 部署文档**
  - [ ] docs/VPS_DEPLOY.md
  - [ ] docs/DOCKER_DEPLOY.md
  - [ ] docs/RAILWAY_DEPLOY.md

- [ ] **8.3 其他文档**
  - [ ] CHANGELOG.md
  - [ ] CONTRIBUTING.md

### 验收标准
- 用户可以按文档完成部署
- 命令参考完整

---

## 错误记录

| 错误 | 尝试次数 | 解决方案 |
|------|----------|---------|
| - | - | - |

---

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-01-19 | 在 tasks/cloudwork 独立开发 | 不影响现有系统运行 |
| 2026-01-19 | 先完成 Phase 1-3 和 8 (MVP) | 最小可用版本优先 |

---

## 下一步行动

1. **立即**: 开始 Phase 1 - 创建目录结构
2. **然后**: 复制并重构现有代码
3. **最后**: 测试容器化部署
