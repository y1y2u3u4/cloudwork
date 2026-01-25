"""
Cron 配置管理

管理 cron 任务的配置，包括任务开关、通知设置等。
"""

import json
import logging
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from ...utils.config import settings

logger = logging.getLogger(__name__)

# 中国时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))


class CronConfig:
    """Cron 配置管理器"""

    def __init__(self):
        self.config_file = Path(settings.work_dir) / "data" / "cron_config.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载 cron 配置失败: {e}")

        # 默认配置
        return {
            "notification": {
                "enabled": True,
                "interval_minutes": 30  # 通知检查间隔（分钟）
            },
            "tasks": {}  # task_id -> task_config
        }

    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存 cron 配置失败: {e}")

    # =====================================
    # 通知设置
    # =====================================

    def is_notification_enabled(self) -> bool:
        """通知是否启用（每次从文件读取最新配置）"""
        self._config = self._load_config()  # 重新加载确保获取最新值
        return self._config.get("notification", {}).get("enabled", True)

    def set_notification_enabled(self, enabled: bool):
        """设置通知开关"""
        if "notification" not in self._config:
            self._config["notification"] = {}
        self._config["notification"]["enabled"] = enabled
        self._save_config()

    def get_notification_interval(self) -> int:
        """获取通知检查间隔（分钟）"""
        return self._config.get("notification", {}).get("interval_minutes", 30)

    def set_notification_interval(self, minutes: int):
        """设置通知检查间隔（分钟）"""
        if "notification" not in self._config:
            self._config["notification"] = {}
        self._config["notification"]["interval_minutes"] = minutes
        self._save_config()

    # =====================================
    # 任务配置
    # =====================================

    def get_task_config(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务配置"""
        return self._config.get("tasks", {}).get(task_id)

    def set_task_config(self, task_id: str, config: Dict[str, Any]):
        """设置任务配置"""
        if "tasks" not in self._config:
            self._config["tasks"] = {}
        self._config["tasks"][task_id] = config
        self._save_config()

    def remove_task_config(self, task_id: str):
        """移除任务配置"""
        if task_id in self._config.get("tasks", {}):
            del self._config["tasks"][task_id]
            self._save_config()

    def is_task_enabled(self, task_id: str) -> bool:
        """任务是否启用"""
        task_config = self.get_task_config(task_id)
        if task_config:
            return task_config.get("enabled", True)
        return True  # 默认启用

    def set_task_enabled(self, task_id: str, enabled: bool):
        """设置任务开关"""
        task_config = self.get_task_config(task_id) or {}
        task_config["enabled"] = enabled
        self.set_task_config(task_id, task_config)

    # =====================================
    # Crontab 操作
    # =====================================

    def get_cron_tasks(self) -> List[Dict[str, Any]]:
        """获取当前 crontab 中的任务列表"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if "no crontab" in result.stderr.lower():
                    return []
                logger.error(f"读取 crontab 失败: {result.stderr}")
                return []

            tasks = []
            lines = result.stdout.strip().split('\n')

            for i, line in enumerate(lines):
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue

                # 解析 cron 表达式和命令
                task_info = self._parse_cron_line(line, i + 1)
                if task_info:
                    # 尝试识别任务类型
                    task_id = self._identify_task_id(task_info["command"])
                    task_info["task_id"] = task_id
                    task_info["enabled"] = self.is_task_enabled(task_id) if task_id else True
                    tasks.append(task_info)

            return tasks

        except Exception as e:
            logger.error(f"获取 cron 任务失败: {e}")
            return []

    def _parse_cron_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析 cron 行"""
        # cron 格式: 分 时 日 月 周 命令
        parts = line.split(None, 5)
        if len(parts) < 6:
            return None

        cron_expr = " ".join(parts[:5])
        command = parts[5]

        # 解析 cron 表达式为人类可读描述
        description = self._describe_cron_expr(cron_expr)

        return {
            "line_num": line_num,
            "cron_expr": cron_expr,
            "command": command,
            "description": description,
            "raw": line
        }

    def _describe_cron_expr(self, expr: str) -> str:
        """将 cron 表达式转换为人类可读描述"""
        parts = expr.split()
        if len(parts) != 5:
            return expr

        minute, hour, day, month, weekday = parts

        # 常见模式
        if expr == "* * * * *":
            return "每分钟"
        elif expr == "0 * * * *":
            return "每小时整点"
        elif expr == "0 0 * * *":
            return "每天 00:00"
        elif minute == "0" and hour != "*" and day == "*" and month == "*" and weekday == "*":
            return f"每天 {hour}:00"
        elif minute != "*" and hour != "*" and day == "*" and month == "*" and weekday == "*":
            return f"每天 {hour}:{minute.zfill(2)}"
        elif expr.startswith("*/"):
            interval = expr.split()[0][2:]
            return f"每 {interval} 分钟"
        elif minute == "0" and hour.startswith("*/"):
            interval = hour[2:]
            return f"每 {interval} 小时"

        return expr

    def _identify_task_id(self, command: str) -> Optional[str]:
        """从命令中识别任务 ID"""
        # 匹配 scripts/cron/ 目录下的脚本
        match = re.search(r'scripts/cron/(\w+)\.sh', command)
        if match:
            script_name = match.group(1)
            # 常见映射
            if "trading" in script_name:
                return "trading_check"
            return script_name

        return None

    def add_cron_task(self, cron_expr: str, command: str) -> bool:
        """添加 cron 任务"""
        try:
            # 获取现有 crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            existing = ""
            if result.returncode == 0:
                existing = result.stdout.strip()

            # 添加新任务
            new_crontab = f"{existing}\n{cron_expr} {command}".strip() + "\n"

            # 写入新 crontab
            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=new_crontab)

            return process.returncode == 0

        except Exception as e:
            logger.error(f"添加 cron 任务失败: {e}")
            return False

    def remove_cron_task(self, line_num: int) -> bool:
        """删除指定行号的 cron 任务"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False

            lines = result.stdout.strip().split('\n')

            # 删除指定行（跳过注释和空行需要调整索引）
            new_lines = []
            current_line = 0
            for line in lines:
                current_line += 1
                if current_line != line_num:
                    new_lines.append(line)

            # 写入新 crontab
            new_crontab = "\n".join(new_lines) + "\n" if new_lines else ""

            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=new_crontab)

            return process.returncode == 0

        except Exception as e:
            logger.error(f"删除 cron 任务失败: {e}")
            return False

    def update_cron_schedule(self, line_num: int, new_cron_expr: str) -> bool:
        """更新任务的执行周期"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return False

            lines = result.stdout.strip().split('\n')

            # 更新指定行
            new_lines = []
            current_line = 0
            for line in lines:
                original_line = line
                line_stripped = line.strip()
                current_line += 1

                if current_line == line_num and line_stripped and not line_stripped.startswith('#'):
                    # 替换 cron 表达式
                    parts = line_stripped.split(None, 5)
                    if len(parts) >= 6:
                        command = parts[5]
                        new_lines.append(f"{new_cron_expr} {command}")
                    else:
                        new_lines.append(original_line)
                else:
                    new_lines.append(original_line)

            # 写入新 crontab
            new_crontab = "\n".join(new_lines) + "\n"

            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=new_crontab)

            return process.returncode == 0

        except Exception as e:
            logger.error(f"更新 cron 任务失败: {e}")
            return False

    def get_pending_notifications_count(self) -> int:
        """获取待处理通知数量"""
        outputs_dir = Path(settings.work_dir) / "data" / "cron_outputs"
        if not outputs_dir.exists():
            return 0
        return len(list(outputs_dir.glob("*.json")))


# 全局实例
cron_config = CronConfig()
