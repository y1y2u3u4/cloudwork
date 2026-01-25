# Trading 自动监控功能

## 功能概述

Bot 会每小时自动检查 Railway Freqtrade 的回测执行结果，并通过 Telegram 发送通知。

## 工作原理

### 定时任务

- **执行频率**: 每小时整点 (如 00:00, 01:00, 02:00 等)
- **调度器**: 使用 APScheduler 实现
- **自动启动**: Bot 启动时自动启动定时任务

### 监控流程

1. **获取 API Token**: 通过 Freqtrade API 认证
2. **查询回测结果**: 调用 `/api/v1/backtest` 接口
3. **检查新结果**: 对比缓存判断是否有新的回测结果
4. **发送通知**: 格式化结果并发送到授权用户
5. **更新缓存**: 记录本次检查的结果 ID

## 核心模块

### 1. scheduler.py - 定时任务调度器

```python
from src.bot.services.scheduler import scheduler

# 添加每小时任务
scheduler.add_cron_job(
    job_id="trading_monitor_hourly",
    func=trading_monitor.check_trading_results,
    hour="*",  # 每小时
    minute="0"  # 整点执行
)
```

**功能**:
- `add_cron_job()`: 添加 cron 定时任务
- `add_interval_job()`: 添加间隔定时任务
- `remove_job()`: 移除任务
- `list_jobs()`: 列出所有任务

### 2. trading_monitor.py - Trading 监控器

```python
from src.bot.services.trading_monitor import TradingMonitor

monitor = TradingMonitor(bot)
await monitor.check_trading_results()
```

**功能**:
- 连接 Freqtrade API
- 查询回测结果
- 智能去重 (避免重复通知)
- 格式化并发送 Telegram 消息

## 配置信息

### Freqtrade API

在 `trading_monitor.py` 中配置:

```python
self.api_url = "https://freqtrade-production-369a.up.railway.app/api/v1"
self.api_user = "admin"
self.api_pass = "Trading@2024"
```

### 缓存文件

缓存文件路径: `data/trading_monitor_cache.json`

用于记录最后一次检查的结果 ID，避免重复通知。

## 消息格式

当有新的回测结果时，Bot 会发送如下格式的消息:

```
📊 Freqtrade 回测结果

策略: MyStrategy
时间: 2026-01-24 12:00:00

核心指标:
- 总交易次数: 150
- 总收益: 1250.50 USDT (12.51%)
- 胜率: 65.33%
- 最大回撤: 8.20%

状态: ✅ 回测完成
```

## 手动触发

除了自动定时执行，也可以手动触发检查:

```bash
# 在 VPS 上通过 Python 调用
cd /home/claude/vps-cloud-runner/tasks/cloudwork
python3 -c "
import asyncio
from telegram import Bot
from src.bot.services.trading_monitor import TradingMonitor
from src.utils.config import settings

async def check():
    bot = Bot(token=settings.telegram_bot_token)
    monitor = TradingMonitor(bot)
    await monitor.check_trading_results()

asyncio.run(check())
"
```

## 部署说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖: `APScheduler>=3.10.4`

### 2. 重启 Bot

由于代码通过 Syncthing 自动同步到 VPS，只需重启服务:

```bash
# 在 VPS 上执行
systemctl restart claude-bot

# 查看日志
journalctl -u claude-bot -f
```

### 3. 验证启动

Bot 启动后会在日志中输出:

```
定时任务已启动: 每小时检查 trading 执行结果
```

## 故障排查

### 日志查看

```bash
# 查看实时日志
journalctl -u claude-bot -f

# 查看最近日志
journalctl -u claude-bot -n 100
```

### 常见问题

**1. API 连接失败**

检查 Freqtrade API 是否可访问:

```bash
curl -u admin:Trading@2024 \
  "https://freqtrade-production-369a.up.railway.app/api/v1/token/login" \
  -X POST
```

**2. 没有收到通知**

- 检查是否配置了 `TELEGRAM_ALLOWED_USERS`
- 检查 Bot Token 是否正确
- 查看日志是否有错误信息

**3. 任务没有运行**

检查调度器状态:

```python
from src.bot.services.scheduler import scheduler
jobs = scheduler.list_jobs()
print(jobs)
```

## 自定义配置

### 修改检查频率

在 `main.py` 的 `post_init()` 函数中修改:

```python
# 改为每 2 小时检查一次
scheduler.add_cron_job(
    job_id="trading_monitor_hourly",
    func=trading_monitor.check_trading_results,
    hour="*/2",  # 每 2 小时
    minute="0"
)

# 或使用间隔任务
scheduler.add_interval_job(
    job_id="trading_monitor_interval",
    func=trading_monitor.check_trading_results,
    hours=2  # 每 2 小时
)
```

### 添加更多定时任务

```python
# 在 post_init() 中添加
scheduler.add_cron_job(
    job_id="daily_report",
    func=send_daily_report,
    hour="9",  # 每天 9 点
    minute="0"
)
```

## 扩展建议

1. **支持多策略**: 监控多个策略的回测结果
2. **性能统计**: 记录历史收益并生成趋势图表
3. **智能提醒**: 当收益或回撤超过阈值时发送警报
4. **实盘监控**: 除了回测，也监控实盘交易状态
