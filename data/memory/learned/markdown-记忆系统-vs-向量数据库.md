# Markdown 记忆系统 vs 向量数据库

**提取日期**: 2026-01-25
**来源**: cloudwork 记忆系统设计
**标签**: architecture, memory, design

## 问题
是否需要向量数据库来实现 Claude 的记忆系统？

## 结论
**不需要**。原因：

1. Claude 本身就擅长读 Markdown，不需要向量检索中间层
2. 记忆量在 1000 条以内时，grep + index.md 搜索足够
3. CLAUDE.md 是原生的记忆注入点，每次启动自动加载
4. 向量库需要 embedding API（成本）+ SQLite-vec（复杂度）

## 推荐方案
三层 Markdown 记忆:
- daily/YYYY-MM-DD.md - 短期记忆（7天自动归档）
- learned/*.md - 中期记忆（可复用模式）
- MEMORY.md - 长期记忆（用户偏好、项目知识）

## 升级路径
如果未来记忆量真的大到需要语义搜索，加 SQLite FTS5（BM25 全文搜索）即可，仍不需要向量库。