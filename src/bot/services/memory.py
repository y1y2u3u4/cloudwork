"""
CloudWork Memory Service

三层记忆管理系统:
- Layer 1: 短期记忆 (daily/) — 每日会话摘要
- Layer 2: 中期记忆 (learned/) — 可复用技术模式
- Layer 3: 长期记忆 (MEMORY.md) — 用户偏好和项目知识

持续学习功能:
- 会话结束时自动提取有价值的模式
- 识别: 错误解决方案、用户纠正、变通方案、调试技巧

记忆遗忘机制:
- 自动清理低价值的旧记忆
- 基于: 时间、重要性、访问频率
"""

import os
import logging
import re
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
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
            existing = f"# {date_obj.strftime('%Y-%m-%d')} 会话记录\n"

        # 查找或创建 section
        section_header = f"## {section}"
        if section_header in existing:
            # 使用正则在 section 末尾追加
            import re
            # 匹配 section header 到下一个 ## 或文件末尾
            pattern = f"({re.escape(section_header)}.*?)(\n## |$)"

            def replacer(match):
                section_content = match.group(1).rstrip()
                next_section = match.group(2)
                return f"{section_content}\n- {content}\n{next_section}"

            existing = re.sub(pattern, replacer, existing, count=1, flags=re.DOTALL)
        else:
            # 创建新 section
            existing = existing.rstrip() + f"\n\n{section_header}\n- {content}\n"

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

    def _is_similar_content(self, existing_text: str, new_content: str, threshold: float = 0.6) -> bool:
        """检查新内容是否与已有内容相似（字符级别的重叠检测）"""
        import re

        def normalize(text):
            # 去除标点和空格，只保留中文、英文、数字
            return re.sub(r'[^\u4e00-\u9fff a-zA-Z0-9]', '', text.lower())

        def get_ngrams(text, n=2):
            """获取 n-gram 集合（用于中文的字符级别匹配）"""
            text = normalize(text)
            if len(text) < n:
                return {text} if text else set()
            return set(text[i:i+n] for i in range(len(text) - n + 1))

        new_ngrams = get_ngrams(new_content)
        if not new_ngrams:
            return False

        # 检查已有内容的每一行
        for line in existing_text.split('\n'):
            if line.strip().startswith('- '):
                # 提取记忆条目内容（去除时间戳）
                line_content = re.sub(r'\[\d{2}-\d{2}\]', '', line)
                line_content = re.sub(r'\[\d{4}-\d{2}-\d{2}.*?\]', '', line_content)
                line_ngrams = get_ngrams(line_content)
                if not line_ngrams:
                    continue
                # 计算 n-gram 重叠率
                overlap = len(new_ngrams & line_ngrams) / len(new_ngrams)
                if overlap >= threshold:
                    return True
        return False

    def append_memory(self, section: str, content: str, check_duplicate: bool = True) -> bool:
        """追加到长期记忆的指定 section

        Args:
            section: 分类名称
            content: 记忆内容
            check_duplicate: 是否检查重复（默认 True）

        Returns:
            bool: 是否成功添加（如果重复则返回 False）
        """
        existing = self.load_memory()

        if not existing:
            existing = "# 长期记忆\n\n"

        # P1 改进: 去重检查
        if check_duplicate and self._is_similar_content(existing, content):
            logger.info(f"Skipped duplicate memory: {content[:50]}...")
            return False

        section_header = f"## {section}"
        timestamp = datetime.now().strftime("%m-%d")  # P2 改进: 简化时间戳
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
        return True

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
        """搜索所有记忆文件，按匹配数降序排列"""
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
                        "matches": matches[:5],  # 每个文件最多 5 个匹配
                        "match_count": len(matches)  # 总匹配数用于排序
                    })
            except Exception as e:
                logger.error(f"Error searching {filepath}: {e}")

        # P1 改进: 按匹配数降序排列
        results.sort(key=lambda x: x["match_count"], reverse=True)
        return results

    # ============ 会话集成 ============

    def get_learned_summaries(self, max_count: int = 3) -> str:
        """获取最近的 learned 模式摘要"""
        patterns = self.list_learned()[:max_count]
        if not patterns:
            return ""

        summaries = []
        for p in patterns:
            try:
                content = Path(p["path"]).read_text(encoding='utf-8')
                # 提取前 200 字符作为摘要
                lines = content.split('\n')
                # 跳过标题和元数据，取实际内容
                summary_lines = []
                for line in lines:
                    if line.startswith('#') or line.startswith('**'):
                        continue
                    if line.strip():
                        summary_lines.append(line.strip())
                    if len('\n'.join(summary_lines)) > 150:
                        break
                summary = '\n'.join(summary_lines)[:150]
                summaries.append(f"**{p['title']}**: {summary}...")
            except Exception as e:
                logger.error(f"Error reading learned pattern {p['path']}: {e}")

        return '\n\n'.join(summaries)

    def get_session_context(self) -> str:
        """
        获取会话开始时需要加载的上下文

        返回: MEMORY.md + 今天/昨天的 daily + learned 摘要 + index
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

        # P2 改进: 加载最近的 learned 模式摘要
        learned_summaries = self.get_learned_summaries(max_count=3)
        if learned_summaries:
            context_parts.append("=== 可用技术模式 ===\n" + learned_summaries)

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

    # ============ 持续学习 - 会话模式提取 ============

    PATTERN_TYPES = {
        "error_resolution": "错误解决方案",
        "user_correction": "用户纠正",
        "workaround": "变通方案",
        "debugging_technique": "调试技巧",
        "project_specific": "项目特定知识",
    }

    async def extract_patterns_from_session(
        self,
        session_transcript: str,
        session_name: str,
        min_length: int = 500
    ) -> List[Dict[str, Any]]:
        """
        从会话记录中提取可复用的模式

        Args:
            session_transcript: 会话文本内容
            session_name: 会话名称
            min_length: 最小文本长度（太短的会话不分析）

        Returns:
            提取的模式列表
        """
        if len(session_transcript) < min_length:
            logger.info(f"会话内容太短 ({len(session_transcript)}字)，跳过模式提取")
            return []

        # 使用 Claude CLI 分析会话
        prompt = f"""分析以下会话记录，提取可复用的技术模式。

会话名称: {session_name}

会话内容:
{session_transcript[:8000]}  # 限制长度避免超出 token

请识别以下类型的模式（只输出确实存在的）：
1. error_resolution - 错误解决方案：如何解决了某个错误
2. user_correction - 用户纠正：用户纠正了 AI 的什么理解
3. workaround - 变通方案：绕过某个问题的技巧
4. debugging_technique - 调试技巧：有效的调试方法
5. project_specific - 项目特定：该项目的特殊约定或知识

输出格式（JSON 数组，如果没有发现任何模式则输出空数组 []）:
```json
[
  {{
    "type": "error_resolution",
    "title": "模式标题（简短描述）",
    "context": "什么情况下会遇到这个问题",
    "solution": "解决方案的详细描述",
    "example": "相关代码示例（如果有）"
  }}
]
```

重要：只提取真正有价值、可复用的模式。普通的对话不需要提取。"""

        try:
            # 调用 Claude CLI
            result = subprocess.run(
                ['claude', '-p', prompt, '--model', 'haiku', '--output-format', 'json'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.data_dir.parent)
            )

            if result.returncode != 0:
                logger.error(f"Claude CLI 执行失败: {result.stderr}")
                return []

            # 解析输出
            output = result.stdout.strip()

            # 尝试从输出中提取 JSON
            patterns = self._parse_patterns_json(output)

            if patterns:
                logger.info(f"从会话 '{session_name}' 提取了 {len(patterns)} 个模式")

            return patterns

        except subprocess.TimeoutExpired:
            logger.warning("模式提取超时")
            return []
        except Exception as e:
            logger.error(f"模式提取失败: {e}")
            return []

    def _parse_patterns_json(self, output: str) -> List[Dict[str, Any]]:
        """从 Claude 输出中解析模式 JSON"""
        import json

        # 尝试直接解析
        try:
            data = json.loads(output)
            if isinstance(data, dict) and "result" in data:
                # Claude CLI JSON 格式
                result_text = data.get("result", "")
                return self._extract_json_from_text(result_text)
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # 从文本中提取 JSON
        return self._extract_json_from_text(output)

    def _extract_json_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取 JSON 数组"""
        import json

        # 查找 JSON 数组
        match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 查找空数组
        if '[]' in text:
            return []

        return []

    def save_extracted_patterns(self, patterns: List[Dict[str, Any]], source: str):
        """保存提取的模式到 learned/ 目录"""
        saved_count = 0

        for pattern in patterns:
            pattern_type = pattern.get("type", "unknown")
            title = pattern.get("title", "未命名模式")

            # 构建内容
            content = f"## 场景\n{pattern.get('context', '无')}\n\n"
            content += f"## 解决方案\n{pattern.get('solution', '无')}\n\n"

            if pattern.get("example"):
                content += f"## 示例\n```\n{pattern['example']}\n```\n"

            # 元数据
            metadata = {
                "source": source,
                "tags": [pattern_type, self.PATTERN_TYPES.get(pattern_type, pattern_type)]
            }

            # 保存
            self.save_learned(title, content, metadata)
            saved_count += 1

        logger.info(f"保存了 {saved_count} 个提取的模式")
        return saved_count

    async def learn_from_session(self, session_transcript: str, session_name: str) -> int:
        """
        从会话中学习（完整流程）

        Args:
            session_transcript: 会话内容
            session_name: 会话名称

        Returns:
            提取并保存的模式数量
        """
        patterns = await self.extract_patterns_from_session(session_transcript, session_name)

        if patterns:
            return self.save_extracted_patterns(patterns, f"session:{session_name}")

        return 0

    # ============ 记忆遗忘机制 ============

    def calculate_memory_score(self, filepath: Path) -> Tuple[float, Dict[str, Any]]:
        """
        计算记忆文件的价值分数

        评分因素:
        - 时间衰减: 越旧分数越低
        - 文件大小: 太小可能价值低
        - 访问频率: 从 git log 或 atime 判断（简化版用 mtime）

        Returns:
            (score, details)
        """
        if not filepath.exists():
            return 0.0, {"reason": "文件不存在"}

        stat = filepath.stat()
        now = datetime.now()

        # 1. 时间因素 (0-40分)
        modified = datetime.fromtimestamp(stat.st_mtime)
        days_old = (now - modified).days

        if days_old <= 7:
            time_score = 40
        elif days_old <= 30:
            time_score = 30
        elif days_old <= 90:
            time_score = 20
        elif days_old <= 180:
            time_score = 10
        else:
            time_score = 5

        # 2. 大小因素 (0-30分)
        size = stat.st_size
        if size < 100:
            size_score = 5  # 太小，可能没价值
        elif size < 500:
            size_score = 15
        elif size < 2000:
            size_score = 30
        else:
            size_score = 25  # 太大可能是杂乱的

        # 3. 内容质量因素 (0-30分)
        try:
            content = filepath.read_text(encoding='utf-8')
            quality_score = self._evaluate_content_quality(content)
        except Exception:
            quality_score = 10

        total_score = time_score + size_score + quality_score

        details = {
            "days_old": days_old,
            "size": size,
            "time_score": time_score,
            "size_score": size_score,
            "quality_score": quality_score,
            "total": total_score
        }

        return total_score, details

    def _evaluate_content_quality(self, content: str) -> int:
        """评估内容质量 (0-30分)"""
        score = 10  # 基础分

        # 有结构化标题
        if re.search(r'^##?\s', content, re.MULTILINE):
            score += 5

        # 有代码块
        if '```' in content:
            score += 5

        # 有实际内容（不只是标题和元数据）
        lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#') and not l.startswith('**')]
        if len(lines) > 5:
            score += 5

        # 有关键词表明是有价值的技术内容
        valuable_keywords = ['解决', '修复', 'fix', 'error', '配置', '命令', 'API', '原因']
        if any(kw in content.lower() for kw in valuable_keywords):
            score += 5

        return min(score, 30)

    def get_forgettable_memories(
        self,
        threshold: float = 30.0,
        max_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取可以遗忘的记忆文件

        Args:
            threshold: 分数低于此阈值的被认为可遗忘
            max_count: 最多返回多少个

        Returns:
            可遗忘的记忆列表
        """
        candidates = []

        # 检查 learned/ 目录
        for filepath in self.learned_dir.glob("*.md"):
            score, details = self.calculate_memory_score(filepath)

            if score < threshold:
                candidates.append({
                    "path": str(filepath),
                    "name": filepath.stem,
                    "score": score,
                    "details": details
                })

        # 检查 daily/archive/ 目录（旧的每日记忆）
        for filepath in self.archive_dir.glob("*.md"):
            score, details = self.calculate_memory_score(filepath)

            # 归档的日志用更低的阈值
            if score < threshold * 0.7:
                candidates.append({
                    "path": str(filepath),
                    "name": f"archive/{filepath.stem}",
                    "score": score,
                    "details": details
                })

        # 按分数升序排列（最低分的最容易被遗忘）
        candidates.sort(key=lambda x: x["score"])

        return candidates[:max_count]

    def forget(
        self,
        memory_path: Optional[str] = None,
        auto: bool = False,
        threshold: float = 25.0,
        dry_run: bool = True
    ) -> List[str]:
        """
        遗忘（删除）低价值记忆

        Args:
            memory_path: 指定要删除的文件路径
            auto: 自动模式，删除所有低于阈值的记忆
            threshold: 自动模式的阈值
            dry_run: 只预览不实际删除

        Returns:
            被删除（或将被删除）的文件路径列表
        """
        deleted = []

        if memory_path:
            # 删除指定文件
            path = Path(memory_path)
            if path.exists():
                if not dry_run:
                    path.unlink()
                    logger.info(f"已删除记忆: {path}")
                deleted.append(str(path))

        elif auto:
            # 自动删除低分记忆
            candidates = self.get_forgettable_memories(threshold=threshold, max_count=20)

            for item in candidates:
                path = Path(item["path"])
                if path.exists():
                    if not dry_run:
                        path.unlink()
                        logger.info(f"自动遗忘: {path} (分数: {item['score']:.1f})")
                    deleted.append(item["path"])

        if deleted and not dry_run:
            # 更新索引
            self._update_index()

        return deleted

    def get_forget_preview(self, threshold: float = 25.0) -> str:
        """
        获取遗忘预览（用户友好的格式）
        """
        candidates = self.get_forgettable_memories(threshold=threshold)

        if not candidates:
            return "没有发现可以遗忘的低价值记忆。"

        text = f"发现 {len(candidates)} 个低价值记忆（分数 < {threshold}）:\n\n"

        for item in candidates:
            text += f"• **{item['name']}** (分数: {item['score']:.0f})\n"
            text += f"  - 天数: {item['details']['days_old']}天\n"
            text += f"  - 大小: {item['details']['size']}字节\n"

        text += "\n使用 `/memory forget --confirm` 执行遗忘。"

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
