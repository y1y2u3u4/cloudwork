# Memory Skill - 三层记忆管理系统

CloudWork 的记忆系统，让 Claude 能够跨会话积累知识和经验。

## 核心理念

**记忆 = 分层的 Markdown 文件 + CLAUDE.md 自动注入**

不使用向量数据库，纯文件系统实现，零外部依赖。

## 三层记忆架构

```
data/memory/
├── daily/                    # Layer 1: 短期记忆（自动）
│   ├── 2026-01-25.md         # 每日会话摘要
│   └── 2026-01-26.md
├── learned/                  # Layer 2: 中期记忆（半自动）
│   ├── python39-typing.md    # 发现的技术模式
│   └── freqtrade-api.md      # 项目特定经验
├── MEMORY.md                 # Layer 3: 长期记忆（策展）
└── index.md                  # 记忆索引（自动生成）
```

### Layer 1: 短期记忆 — `daily/YYYY-MM-DD.md`

- **触发**: 每次会话结束自动写入
- **内容**: 今天做了什么、遇到什么问题、怎么解决的
- **保留**: 7 天后自动归档
- **加载**: 会话开始时读取 "昨天" + "今天" 的记录

格式示例:
```markdown
# 2026-01-25 会话记录

## 完成的任务
- 修复了 tool_display 显示 bug
- 优化了 cron 通知配置

## 遇到的问题
- 周期性更新覆盖格式化显示 → 通过 current_tool_display 字段解决

## 学到的经验
- systemd 服务可以 kill 进程让它自动重启（Restart=always）

## 下次继续
- 实现记忆系统
```

### Layer 2: 中期记忆 — `learned/*.md`

- **触发**: `/memory learn` 手动提取，或会话中发现可复用模式
- **内容**: 可复用的技术模式、bug 解决方案、项目特定经验
- **用途**: Claude 按需读取相关模式

格式示例:
```markdown
# Python 3.9 类型注解兼容性

**提取日期**: 2026-01-25
**来源**: cloudwork 项目开发

## 问题
VPS 运行 Python 3.9，部分类型注解语法不兼容。

## 解决方案
使用 typing 模块的兼容写法:
- `Optional[str]` 而不是 `str | None`
- `Tuple[str, str]` 而不是 `tuple[str, str]`
- `List[int]` 而不是 `list[int]`

## 适用场景
当目标环境是 Python 3.9 或更早版本时。
```

### Layer 3: 长期记忆 — `MEMORY.md`

- **触发**: `/memory save` 手动策展
- **内容**: 用户偏好、项目架构决策、关键配置
- **用途**: 永久性知识，会话开始时自动加载

格式示例:
```markdown
# 长期记忆

## 用户偏好
- 代码风格: 简洁，避免过度工程化
- 语言: 中文交流，代码注释用中文
- 提交信息: 使用中文 + Co-Authored-By

## 项目知识

### CloudWork
- 架构: Telegram Bot → Claude CLI → 会话管理
- 部署: VPS + systemd，Syncthing 同步代码
- Git: SSH 推送到 GitHub

### Freqtrade
- Railway 部署，Volume 存储策略
- 通过 SSH 热更新策略文件，不走 Git
```

## 命令用法

### `/memory` — 查看记忆状态

显示各层记忆的数量和最近更新时间。

输出示例:
```
📚 记忆系统状态

短期记忆 (daily/):
  - 今天: 3 条记录
  - 昨天: 5 条记录
  - 总计: 12 个文件

中期记忆 (learned/):
  - 总计: 8 个模式
  - 最近: python39-typing.md (2 天前)

长期记忆 (MEMORY.md):
  - 用户偏好: 5 条
  - 项目知识: 3 个项目
  - 最后更新: 2026-01-24
```

### `/memory learn [描述]` — 提取可复用模式

从当前会话中提取值得保存的技术模式。

触发条件:
- 解决了一个非平凡的 bug
- 发现了框架/库的 workaround
- 总结了项目特定的约定

示例:
```
/memory learn 解决了 tool_display 被周期性更新覆盖的问题
```

Claude 会:
1. 分析当前会话中的解决方案
2. 提取核心模式
3. 保存到 `learned/tool-display-update-pattern.md`

### `/memory save <内容>` — 保存长期记忆

手动添加一条永久性记忆到 MEMORY.md。

示例:
```
/memory save 用户偏好: 不要自动添加 docstring
```

### `/memory search <关键词>` — 搜索记忆

在所有记忆文件中搜索关键词。

示例:
```
/memory search freqtrade
```

### `/memory sync` — 同步到 CLAUDE.md

将高频使用的记忆同步到项目的 CLAUDE.md，确保每次 Claude 启动自动加载。

## 自动化流程

### 会话开始时

Claude 自动读取:
1. `MEMORY.md` — 长期记忆
2. `daily/今天.md` — 今天的记录
3. `daily/昨天.md` — 昨天的记录
4. `index.md` — 记忆索引（知道有哪些 learned 模式可用）

### 会话结束时

自动写入 `daily/YYYY-MM-DD.md`:
- 本次会话完成的任务
- 遇到的问题和解决方案
- 下次需要继续的工作

### 定期维护

- 7 天前的 daily 记录自动归档到 `daily/archive/`
- 高频引用的 learned 模式提示同步到 CLAUDE.md

## 与 CLAUDE.md 的关系

CLAUDE.md 是 Claude Code 的 **原生记忆注入点**:
- 每次 Claude 启动自动加载
- 不需要额外的 API 调用
- 最可靠的长期记忆存储

**同步策略**:
- 核心用户偏好 → 直接写入 CLAUDE.md
- 项目架构知识 → 写入 CLAUDE.md
- 临时性记录 → 保留在 MEMORY.md/daily/

## 设计原则

1. **零外部依赖**: 不需要向量数据库、不需要 embedding API
2. **Claude 原生友好**: Markdown 是 Claude 最擅长处理的格式
3. **搜索够用**: grep + index.md 足以应对几百个记忆文件
4. **渐进式升级**: 未来如需语义搜索，加 SQLite FTS5 即可

## 实现说明

Bot 代码位置:
- `src/bot/services/memory.py` — MemoryManager 类
- `src/bot/handlers/commands.py` — /memory 命令注册
- `src/bot/handlers/messages.py` — 会话开始/结束时的记忆加载/保存
