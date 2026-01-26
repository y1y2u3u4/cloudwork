"""
CloudWork Memory Service

三层记忆管理系统:
- Layer 1: 短期记忆 (daily/) — 每日会话摘要
- Layer 2: 中期记忆 (learned/) — 可复用技术模式
- Layer 3: 长期记忆 (MEMORY.md) — 用户偏好和项目知识
"""

import os
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryManager:
    """三层记忆管理器"""

    def __init__(self, data_dir: str):
        """
        初始化记忆管理器

        Args:
            data_dir: 数据目录路径 (通常是 cloudwork/data)
        """
        self.data_dir = Path(data_dir)
        self.memory_dir = self.data_dir / "memory"
        self.daily_dir = self.memory_dir / "daily"
        self.learned_dir = self.memory_dir / "learned"
        self.archive_dir = self.daily_dir / "archive"
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.index_file = self.memory_dir / "index.md"

        # 确保目录存在
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保所有必要的目录存在"""
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.learned_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ============ Layer 1: 短期记忆 (Daily) ============

    def get_daily_file(self, date: Optional[datetime] = None) -> Path:
        """获取指定日期的记忆文件路径"""
        if date is None:
            date = datetime.now()
        return self.daily_dir / f"{date.strftime('%Y-%m-%d')}.md"

    def load_daily(self, date: Optional[datetime] = None) -> str:
        """加载指定日期的记忆"""
        filepath = self.get_daily_file(date)
        if filepath.exists():
            return filepath.read_text(encoding='utf-8')
        return ""

    def save_daily(self, content: str, date: Optional[datetime] = None):
        """保存每日记忆"""
        filepath = self.get_daily_file(date)
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Saved daily memory: {filepath.name}")

    def append_daily(self, section: str, content: str, date: Optional[datetime] = None):
        """追加内容到每日记忆的指定 section"""
        filepath = self.get_daily_file(date)

        if filepath.exists():
            existing = filepath.read_text(encoding='utf-8')
        else:
            # 创建新的每日文件
            date_obj = date or datetime.now()
            existing = f"# {date_obj.strftime('%Y-%m-%d')} 会话记录\n\n"

        # 查找或创建 section
        section_header = f"## {section}"
        if section_header in existing:
            # 在 section 末尾追加
            lines = existing.split('\n')
            result = []
            in_section = False
            added = False

            for i, line in enumerate(lines):
                result.append(line)
                if line.startswith(section_header):
                    in_section = True
                elif in_section and line.startswith('## '):
                    # 新 section 开始，在这之前插入
                    if not added:
                        result.insert(-1, f"- {content}")
                        result.insert(-1, "")
                        added = True
                    in_section = False

            if in_section and not added:
                # section 在文件末尾
                result.append(f"- {content}")

            existing = '\n'.join(result)
        else:
            # 创建新 section
            existing += f"\n{section_header}\n- {content}\n"

        filepath.write_text(existing, encoding='utf-8')
        logger.info(f"Appended to daily memory: {section}")

    def get_recent_daily(self, days: int = 2) -> str:
        """获取最近几天的记忆（用于会话开始时加载）"""
        memories = []
        today = datetime.now()

        for i in range(days):
            date = today - timedelta(days=i)
            content = self.load_daily(date)
            if content:
                memories.append(content)

        return "\n\n---\n\n".join(memories)

    def archive_old_daily(self, keep_days: int = 7):
        """归档旧的每日记忆"""
        today = datetime.now()
        cutoff = today - timedelta(days=keep_days)

        archived_count = 0
        for filepath in self.daily_dir.glob("*.md"):
            if filepath.name == "archive":
                continue

            try:
                date_str = filepath.stem  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    # 移动到归档目录
                    archive_path = self.archive_dir / filepath.name
                    filepath.rename(archive_path)
                    archived_count += 1
                    logger.info(f"Archived: {filepath.name}")
            except ValueError:
                continue

        if archived_count > 0:
            logger.info(f"Archived {archived_count} daily memory files")

        return archived_count

    # ============ Layer 2: 中期记忆 (Learned) ============

    def save_learned(self, name: str, content: str, metadata: Optional[Dict] = None):
        """保存学习到的模式"""
        # 规范化文件名
        safe_name = re.sub(r'[^\w\-]', '-', name.lower())
        filepath = self.learned_dir / f"{safe_name}.md"

        # 构建文件内容
        header = f"# {name}\n\n"
        header += f"**提取日期**: {datetime.now().strftime('%Y-%m-%d')}\n"

        if metadata:
            if "source" in metadata:
                header += f"**来源**: {metadata['source']}\n"
            if "tags" in metadata:
                header += f"**标签**: {', '.join(metadata['tags'])}\n"

        header += "\n"

        full_content = header + content
        filepath.write_text(full_content, encoding='utf-8')
        logger.info(f"Saved learned pattern: {filepath.name}")

        # 更新索引
        self._update_index()

        return filepath

    def load_learned(self, name: str) -> Optional[str]:
        """加载指定的学习模式"""
        safe_name = re.sub(r'[^\w\-]', '-', name.lower())
        filepath = self.learned_dir / f"{safe_name}.md"

        if filepath.exists():
            return filepath.read_text(encoding='utf-8')

        # 尝试模糊匹配
        for f in self.learned_dir.glob("*.md"):
            if safe_name in f.stem:
                return f.read_text(encoding='utf-8')

        return None

    def list_learned(self) -> List[Dict[str, Any]]:
        """列出所有学习的模式"""
        patterns = []

        for filepath in self.learned_dir.glob("*.md"):
            stat = filepath.stat()

            # 读取第一行作为标题
            content = filepath.read_text(encoding='utf-8')
            first_line = content.split('\n')[0] if content else ""
            title = first_line.lstrip('#').strip() if first_line.startswith('#') else filepath.stem

            patterns.append({
                "name": filepath.stem,
                "title": title,
                "path": str(filepath),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime)
            })

        # 按修改时间排序
        patterns.sort(key=lambda x: x["modified"], reverse=True)
        return patterns

    # ============ Layer 3: 长期记忆 (MEMORY.md) ============

    def load_memory(self) -> str:
        """加载长期记忆"""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding='utf-8')
        return ""

    def save_memory(self, content: str):
        """保存长期记忆"""
        self.memory_file.write_text(content, encoding='utf-8')
        logger.info("Saved long-term memory")

    def append_memory(self, section: str, content: str):
        """追加到长期记忆的指定 section"""
        existing = self.load_memory()

        if not existing:
            existing = "# 长期记忆\n\n"

        section_header = f"## {section}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- [{timestamp}] {content}"

        if section_header in existing:
            # 在 section 末尾追加
            parts = existing.split(section_header)
            before = parts[0]
            after = parts[1]

            # 找到下一个 ## 或文件末尾
            next_section = after.find('\n## ')
            if next_section == -1:
                # 文件末尾
                after = after.rstrip() + f"\n{entry}\n"
            else:
                # 在下一个 section 前插入
                after = after[:next_section].rstrip() + f"\n{entry}\n" + after[next_section:]

            existing = before + section_header + after
        else:
            # 创建新 section
            existing = existing.rstrip() + f"\n\n{section_header}\n{entry}\n"

        self.save_memory(existing)
        logger.info(f"Appended to memory section: {section}")

    # ============ 索引管理 ============

    def _update_index(self):
        """更新记忆索引文件"""
        content = "# 记忆索引\n\n"
        content += f"*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"

        # 长期记忆摘要
        content += "## 长期记忆 (MEMORY.md)\n\n"
        if self.memory_file.exists():
            memory = self.load_memory()
            # 提取 section 标题
            sections = re.findall(r'^## (.+)$', memory, re.MULTILINE)
            for section in sections:
                content += f"- {section}\n"
        else:
            content += "*暂无长期记忆*\n"
        content += "\n"

        # 学习模式列表
        content += "## 学习模式 (learned/)\n\n"
        patterns = self.list_learned()
        if patterns:
            for p in patterns[:20]:  # 最多显示 20 个
                content += f"- **{p['title']}** ({p['name']}.md) - {p['modified'].strftime('%Y-%m-%d')}\n"
        else:
            content += "*暂无学习模式*\n"
        content += "\n"

        # 近期每日记忆
        content += "## 近期会话 (daily/)\n\n"
        daily_files = sorted(self.daily_dir.glob("*.md"), reverse=True)[:7]
        if daily_files:
            for f in daily_files:
                if f.name != "archive":
                    content += f"- {f.stem}\n"
        else:
            content += "*暂无会话记录*\n"

        self.index_file.write_text(content, encoding='utf-8')
        logger.debug("Updated memory index")

    def load_index(self) -> str:
        """加载记忆索引"""
        if self.index_file.exists():
            return self.index_file.read_text(encoding='utf-8')
        self._update_index()
        return self.index_file.read_text(encoding='utf-8')

    # ============ 搜索功能 ============

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索所有记忆文件"""
        results = []
        keyword_lower = keyword.lower()

        # 搜索所有 .md 文件
        search_paths = [
            self.memory_file,
            *self.daily_dir.glob("*.md"),
            *self.learned_dir.glob("*.md")
        ]

        for filepath in search_paths:
            if not filepath.exists() or not filepath.is_file():
                continue

            try:
                content = filepath.read_text(encoding='utf-8')
                if keyword_lower in content.lower():
                    # 找到匹配的行
                    matches = []
                    for i, line in enumerate(content.split('\n'), 1):
                        if keyword_lower in line.lower():
                            matches.append({
                                "line": i,
                                "text": line.strip()[:100]  # 截断
                            })

                    results.append({
                        "file": str(filepath.relative_to(self.memory_dir)),
                        "matches": matches[:5]  # 每个文件最多 5 个匹配
                    })
            except Exception as e:
                logger.error(f"Error searching {filepath}: {e}")

        return results

    # ============ 会话集成 ============

    def get_session_context(self) -> str:
        """
        获取会话开始时需要加载的上下文

        返回: MEMORY.md + 今天/昨天的 daily + index 摘要
        """
        context_parts = []

        # 长期记忆
        memory = self.load_memory()
        if memory:
            context_parts.append("=== 长期记忆 ===\n" + memory)

        # 近期会话
        recent = self.get_recent_daily(days=2)
        if recent:
            context_parts.append("=== 近期会话 ===\n" + recent)

        # 索引摘要
        index = self.load_index()
        if index:
            context_parts.append("=== 可用记忆索引 ===\n" + index)

        return "\n\n".join(context_parts)

    def save_session_summary(self, summary: str):
        """保存会话摘要到今天的 daily 文件"""
        today = datetime.now()
        filepath = self.get_daily_file(today)

        if filepath.exists():
            existing = filepath.read_text(encoding='utf-8')
            # 追加到末尾
            existing = existing.rstrip() + f"\n\n---\n\n{summary}\n"
        else:
            existing = f"# {today.strftime('%Y-%m-%d')} 会话记录\n\n{summary}\n"

        filepath.write_text(existing, encoding='utf-8')
        logger.info("Saved session summary")

        # 更新索引
        self._update_index()

    # ============ 状态查询 ============

    def get_status(self) -> Dict[str, Any]:
        """获取记忆系统状态"""
        status = {
            "daily": {
                "count": len(list(self.daily_dir.glob("*.md"))),
                "today_exists": self.get_daily_file().exists(),
                "archive_count": len(list(self.archive_dir.glob("*.md")))
            },
            "learned": {
                "count": len(list(self.learned_dir.glob("*.md"))),
                "patterns": [p["title"] for p in self.list_learned()[:5]]
            },
            "memory": {
                "exists": self.memory_file.exists(),
                "size": self.memory_file.stat().st_size if self.memory_file.exists() else 0
            }
        }

        return status

    def format_status(self) -> str:
        """格式化状态为用户可读的文本"""
        status = self.get_status()

        text = "📚 **记忆系统状态**\n\n"

        # 短期记忆
        text += "**短期记忆 (daily/)**\n"
        text += f"  - 文件数: {status['daily']['count']}\n"
        text += f"  - 今天: {'✅ 有记录' if status['daily']['today_exists'] else '❌ 暂无'}\n"
        text += f"  - 归档: {status['daily']['archive_count']} 个文件\n\n"

        # 中期记忆
        text += "**中期记忆 (learned/)**\n"
        text += f"  - 模式数: {status['learned']['count']}\n"
        if status['learned']['patterns']:
            text += f"  - 最近: {', '.join(status['learned']['patterns'][:3])}\n"
        text += "\n"

        # 长期记忆
        text += "**长期记忆 (MEMORY.md)**\n"
        if status['memory']['exists']:
            text += f"  - 大小: {status['memory']['size']} bytes\n"
        else:
            text += "  - ❌ 尚未创建\n"

        return text


# 全局实例
memory_manager: Optional[MemoryManager] = None


def init_memory(data_dir: str):
    """初始化记忆管理器"""
    global memory_manager
    memory_manager = MemoryManager(data_dir)
    logger.info(f"Memory manager initialized: {data_dir}/memory")
    return memory_manager


def get_memory_manager() -> Optional[MemoryManager]:
    """获取记忆管理器实例"""
    return memory_manager
