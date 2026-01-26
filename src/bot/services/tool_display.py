"""
工具调用详情格式化

将 Claude 的工具调用显示为用户友好的格式，包括工具图标和关键参数。
"""

from typing import Dict, Any


class ToolDisplayFormatter:
    """工具调用详情格式化器"""

    # 工具图标映射
    TOOL_ICONS = {
        # 文件操作
        "Read": "📖",
        "Write": "✏️",
        "Edit": "🔧",
        "Glob": "📂",
        "NotebookEdit": "📓",

        # 搜索
        "Grep": "🔍",
        "WebSearch": "🔎",
        "WebFetch": "🌐",

        # 执行
        "Bash": "💻",
        "Task": "📋",

        # 其他
        "TodoWrite": "✅",
        "AskUserQuestion": "❓",
    }

    def format(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        格式化工具调用为用户友好的显示

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            格式化后的字符串，如 "📖 读取 `.../handlers/commands.py`"
        """
        icon = self.TOOL_ICONS.get(tool_name, "🔧")

        if tool_name == "Read":
            path = self._short_path(tool_input.get("file_path", ""))
            return f"{icon} 读取 `{path}`"

        elif tool_name == "Write":
            path = self._short_path(tool_input.get("file_path", ""))
            return f"{icon} 写入 `{path}`"

        elif tool_name == "Edit":
            path = self._short_path(tool_input.get("file_path", ""))
            old_str = tool_input.get("old_string", "")
            # 显示要替换的内容片段
            snippet = old_str[:25].replace('\n', ' ').strip()
            if len(old_str) > 25:
                snippet += "..."
            if snippet:
                return f"{icon} 编辑 `{path}` ({snippet})"
            return f"{icon} 编辑 `{path}`"

        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")
            # 截取命令的关键部分
            cmd_preview = self._short_command(cmd)
            return f"{icon} 执行 `{cmd_preview}`"

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            path = tool_input.get("path", ".")
            path_short = self._short_path(path) if path != "." else "."
            pattern_preview = pattern[:30] if len(pattern) <= 30 else pattern[:27] + "..."
            return f"{icon} 搜索 `{pattern_preview}` in {path_short}"

        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            path = tool_input.get("path", "")
            if path:
                return f"{icon} 查找 `{pattern}` in {self._short_path(path)}"
            return f"{icon} 查找 `{pattern}`"

        elif tool_name == "WebSearch":
            query = tool_input.get("query", "")
            query_preview = query[:35] if len(query) <= 35 else query[:32] + "..."
            return f"{icon} 搜索 `{query_preview}`"

        elif tool_name == "WebFetch":
            url = tool_input.get("url", "")
            # 提取域名
            domain = self._extract_domain(url)
            return f"{icon} 获取 `{domain}`"

        elif tool_name == "Task":
            desc = tool_input.get("description", "")
            desc_preview = desc[:30] if len(desc) <= 30 else desc[:27] + "..."
            return f"{icon} 子任务: {desc_preview}"

        elif tool_name == "TodoWrite":
            todos = tool_input.get("todos", [])
            count = len(todos)
            return f"{icon} 更新任务列表 ({count} 项)"

        elif tool_name == "AskUserQuestion":
            questions = tool_input.get("questions", [])
            if questions:
                first_q = questions[0].get("question", "")[:30]
                return f"{icon} 询问: {first_q}..."
            return f"{icon} 询问用户"

        elif tool_name == "NotebookEdit":
            path = self._short_path(tool_input.get("notebook_path", ""))
            return f"{icon} 编辑 Notebook `{path}`"

        else:
            # 未知工具，尝试显示第一个参数
            if tool_input:
                first_key = list(tool_input.keys())[0]
                first_val = str(tool_input[first_key])[:30]
                return f"{icon} {tool_name}: {first_val}"
            return f"{icon} {tool_name}"

    def _short_path(self, path: str, max_len: int = 35) -> str:
        """缩短路径显示"""
        if not path:
            return ""
        if len(path) <= max_len:
            return path

        # 保留文件名和部分路径
        parts = path.split("/")
        filename = parts[-1]

        if len(filename) > max_len - 4:
            # 文件名太长，截断文件名
            return "..." + filename[-(max_len - 3):]

        # 尝试保留最后两级目录
        if len(parts) >= 2:
            last_two = "/".join(parts[-2:])
            if len(last_two) <= max_len - 4:
                return ".../" + last_two

        return ".../" + filename

    def _short_command(self, cmd: str, max_len: int = 40) -> str:
        """缩短命令显示"""
        if not cmd:
            return ""

        # 移除换行，只取第一行
        cmd = cmd.split('\n')[0].strip()

        if len(cmd) <= max_len:
            return cmd

        # 尝试在空格处截断
        truncated = cmd[:max_len]
        last_space = truncated.rfind(' ')
        if last_space > max_len - 15:
            truncated = truncated[:last_space]

        return truncated + "..."

    def _extract_domain(self, url: str) -> str:
        """提取 URL 的域名"""
        if not url:
            return ""

        # 移除协议
        url = url.replace("https://", "").replace("http://", "")

        # 取域名部分
        domain = url.split("/")[0]

        # 如果太长，截断
        if len(domain) > 30:
            domain = domain[:27] + "..."

        return domain


# 全局实例
tool_formatter = ToolDisplayFormatter()
