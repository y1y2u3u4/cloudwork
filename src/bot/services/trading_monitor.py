"""
Trading 云端执行结果监控

定时查看 Railway Freqtrade 的回测结果并通过 Telegram 发送通知。
"""

import asyncio
import logging
import json
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from telegram import Bot
from telegram.constants import ParseMode

from ...utils.config import settings

logger = logging.getLogger(__name__)


class TradingMonitor:
    """Trading 监控器"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.api_url = "https://freqtrade-production-369a.up.railway.app/api/v1"
        self.api_user = "admin"
        self.api_pass = "Trading@2024"
        self._last_check_time = None
        self._cache_file = Path(settings.work_dir) / "data" / "trading_monitor_cache.json"
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)

    async def check_trading_results(self):
        """检查 trading 执行结果"""
        try:
            logger.info("开始检查 trading 执行结果...")

            # 获取 API Token
            token = await self._get_api_token()
            if not token:
                logger.error("无法获取 API Token")
                return

            # 查询回测结果
            backtest_result = await self._get_backtest_result(token)
            if not backtest_result:
                logger.info("没有新的回测结果")
                return

            # 检查是否是新结果
            if not self._is_new_result(backtest_result):
                logger.info("结果未更新，跳过通知")
                return

            # 格式化并发送通知
            message = self._format_backtest_message(backtest_result)
            await self._send_notification(message)

            # 更新缓存
            self._update_cache(backtest_result)

            logger.info("Trading 结果检查完成")

        except Exception as e:
            logger.error(f"检查 trading 结果失败: {e}", exc_info=True)
            # 发送错误通知
            await self._send_error_notification(str(e))

    async def _get_api_token(self) -> Optional[str]:
        """获取 Freqtrade API Token"""
        try:
            cmd = [
                "curl", "-s", "-u", f"{self.api_user}:{self.api_pass}",
                f"{self.api_url}/token/login",
                "-X", "POST"
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"获取 Token 失败: {stderr.decode()}")
                return None

            data = json.loads(stdout.decode())
            return data.get('access_token')

        except Exception as e:
            logger.error(f"获取 API Token 异常: {e}")
            return None

    async def _get_backtest_result(self, token: str) -> Optional[Dict[str, Any]]:
        """查询回测结果"""
        try:
            cmd = [
                "curl", "-s",
                "-H", f"Authorization: Bearer {token}",
                f"{self.api_url}/backtest"
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.error(f"查询回测结果失败: {stderr.decode()}")
                return None

            data = json.loads(stdout.decode())

            # 检查是否有回测结果
            if data.get('status') == 'running':
                logger.info("回测正在运行中...")
                return None
            elif data.get('status') == 'ended':
                return data
            else:
                logger.info(f"回测状态: {data.get('status', 'unknown')}")
                return None

        except Exception as e:
            logger.error(f"查询回测结果异常: {e}")
            return None

    def _is_new_result(self, result: Dict[str, Any]) -> bool:
        """检查是否是新结果"""
        # 读取缓存
        if not self._cache_file.exists():
            return True

        try:
            with open(self._cache_file, 'r') as f:
                cache = json.load(f)

            # 比较时间戳或结果哈希
            last_run_id = cache.get('run_id')
            current_run_id = result.get('backtest_result_id', result.get('backtest_start_time'))

            return last_run_id != current_run_id

        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return True

    def _update_cache(self, result: Dict[str, Any]):
        """更新缓存"""
        try:
            cache = {
                'run_id': result.get('backtest_result_id', result.get('backtest_start_time')),
                'last_check': datetime.now().isoformat()
            }

            with open(self._cache_file, 'w') as f:
                json.dump(cache, f, indent=2)

        except Exception as e:
            logger.warning(f"更新缓存失败: {e}")

    def _format_backtest_message(self, result: Dict[str, Any]) -> str:
        """格式化回测结果消息"""
        # 提取关键指标
        strategy = result.get('strategy', 'Unknown')
        backtest_result = result.get('backtest_result', {})

        # 从结果中提取统计数据
        stats = {}
        if isinstance(backtest_result, dict):
            # 尝试从不同可能的结构中提取数据
            strategy_stats = backtest_result.get(strategy, {})
            if strategy_stats:
                stats = strategy_stats
            else:
                stats = backtest_result

        # 提取指标
        total_trades = stats.get('total_trades', stats.get('trades', 0))
        profit_total = stats.get('profit_total', stats.get('profit_abs', 0))
        profit_total_pct = stats.get('profit_total_pct', stats.get('profit_total_abs', 0))
        win_rate = stats.get('wins', 0) / max(total_trades, 1) * 100 if total_trades > 0 else 0
        max_drawdown = stats.get('max_drawdown', stats.get('max_drawdown_abs', 0))

        # 格式化消息
        message = f"""📊 **Freqtrade 回测结果**

**策略**: {strategy}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**核心指标**:
- 总交易次数: {total_trades}
- 总收益: {profit_total:.2f} USDT ({profit_total_pct:.2f}%)
- 胜率: {win_rate:.2f}%
- 最大回撤: {abs(max_drawdown):.2f}%

**状态**: ✅ 回测完成
"""

        return message

    async def _send_notification(self, message: str):
        """发送通知到授权用户"""
        allowed_users = settings.telegram_allowed_users
        if not allowed_users:
            logger.warning("没有配置授权用户，跳过通知")
            return

        for user_id in allowed_users:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"已发送通知到用户 {user_id}")
            except Exception as e:
                logger.error(f"发送通知到用户 {user_id} 失败: {e}")

    async def _send_error_notification(self, error_msg: str):
        """发送错误通知"""
        message = f"""⚠️ **Trading 监控异常**

{error_msg}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send_notification(message)
