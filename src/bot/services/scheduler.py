"""
定时任务调度器

使用 APScheduler 实现定时任务调度。
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs: Dict[str, Any] = {}
        self._running = False

    def start(self):
        """启动调度器"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("定时任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("定时任务调度器已关闭")

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str = None,
        hour: str = None,
        minute: str = None,
        **kwargs
    ):
        """
        添加 cron 定时任务

        Args:
            job_id: 任务唯一标识
            func: 要执行的异步函数
            cron_expression: cron 表达式，如 "0 * * * *" (每小时)
            hour: 小时，如 "*/1" (每小时), "*" (每小时), "0,6,12,18" (特定时刻)
            minute: 分钟，如 "0" (整点)
            **kwargs: 传递给 func 的参数
        """
        # 构建 cron 触发器
        if cron_expression:
            # 解析 cron 表达式: minute hour day month day_of_week
            parts = cron_expression.split()
            if len(parts) >= 2:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2] if len(parts) > 2 else '*',
                    month=parts[3] if len(parts) > 3 else '*',
                    day_of_week=parts[4] if len(parts) > 4 else '*'
                )
            else:
                raise ValueError(f"Invalid cron expression: {cron_expression}")
        else:
            trigger = CronTrigger(
                hour=hour or '*',
                minute=minute or '0'
            )

        # 添加任务
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs,
            replace_existing=True
        )

        self._jobs[job_id] = job
        logger.info(f"添加定时任务: {job_id}, 触发器: {trigger}")

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        **kwargs
    ):
        """
        添加间隔定时任务

        Args:
            job_id: 任务唯一标识
            func: 要执行的异步函数
            hours: 间隔小时数
            minutes: 间隔分钟数
            seconds: 间隔秒数
            **kwargs: 传递给 func 的参数
        """
        trigger = IntervalTrigger(
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )

        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs,
            replace_existing=True
        )

        self._jobs[job_id] = job
        logger.info(f"添加间隔任务: {job_id}, 间隔: {hours}h {minutes}m {seconds}s")

    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"移除定时任务: {job_id}")

    def list_jobs(self) -> list:
        """列出所有任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs


# 全局调度器实例
scheduler = TaskScheduler()
