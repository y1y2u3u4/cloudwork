#!/bin/bash
# check_trading.sh - 检查 Freqtrade Dry Run 运行状态
# 由 cron 定时调用，输出 JSON 到 data/cron_outputs/

set -e

# 使用中国时区
export TZ='Asia/Shanghai'

# 配置
API_URL="https://freqtrade-production-369a.up.railway.app/api/v1"
API_USER="admin"
API_PASS="Trading@2024"
OUTPUT_DIR="/home/claude/vps-cloud-runner/tasks/cloudwork/data/cron_outputs"
CACHE_FILE="/home/claude/vps-cloud-runner/tasks/cloudwork/data/trading_check_cache.json"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 生成输出文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/trading_${TIMESTAMP}.json"

# 辅助函数：输出 JSON 通知
output_notification() {
    local status="$1"
    local title="$2"
    local message="$3"

    cat > "$OUTPUT_FILE" << EOF
{
    "task": "trading_check",
    "status": "$status",
    "title": "$title",
    "message": "$message",
    "created_at": "$(date -Iseconds)"
}
EOF
    echo "通知已写入: $OUTPUT_FILE"
}

# 获取 API Token
get_token() {
    curl -s -u "$API_USER:$API_PASS" "$API_URL/token/login" -X POST | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null
}

# 主流程
main() {
    echo "$(date): 开始检查 trading dry run 状态..."

    # 获取 Token
    TOKEN=$(get_token)
    if [ -z "$TOKEN" ]; then
        output_notification "error" "Trading API 错误" "无法获取 API Token，请检查 Freqtrade 服务状态"
        exit 1
    fi

    # 获取数据
    PROFIT_DATA=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/profit" 2>/dev/null)
    STATUS_DATA=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/status" 2>/dev/null)
    BALANCE_DATA=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/balance" 2>/dev/null)

    # 将数据保存到临时文件避免 heredoc 问题
    TMPDIR=$(mktemp -d)
    echo "$PROFIT_DATA" > "$TMPDIR/profit.json"
    echo "$STATUS_DATA" > "$TMPDIR/status.json"
    echo "$BALANCE_DATA" > "$TMPDIR/balance.json"

    # 生成报告
    REPORT=$(python3 << PYREPORT
import json
from datetime import datetime

with open("$TMPDIR/profit.json") as f:
    profit = json.load(f)
with open("$TMPDIR/status.json") as f:
    status = json.load(f)
with open("$TMPDIR/balance.json") as f:
    balance = json.load(f)

lines = []

# === 账户概览 ===
total_stake = balance.get('total', 0)
free_stake = 0
for cur in balance.get('currencies', []):
    if cur.get('currency') == 'USDT' and not cur.get('is_position'):
        free_stake = cur.get('free', 0)
        break

all_profit = profit.get('profit_all_coin', 0)
all_pct = profit.get('profit_all_percent', 0)

# 收益状态指示
if all_pct > 1:
    trend = "📈"
elif all_pct > 0:
    trend = "↗️"
elif all_pct > -1:
    trend = "↘️"
else:
    trend = "📉"

lines.append(f"{trend} 收益: {all_profit:+.2f} USDT ({all_pct:+.2f}%)")

# === 当前持仓详情 ===
positions = status if isinstance(status, list) else []
if positions:
    lines.append(f"📊 持仓 ({len(positions)}个):")
    for pos in positions[:3]:
        pair = pos.get('pair', 'N/A').replace('/USDT:USDT', '')
        direction = "🔴空" if pos.get('is_short') else "🟢多"
        pnl = pos.get('profit_abs', 0)
        pnl_pct = pos.get('profit_pct', 0)
        leverage = pos.get('leverage', 1)

        # 持仓时长
        open_ts = pos.get('open_timestamp', 0)
        if open_ts:
            duration_min = int((datetime.now().timestamp() * 1000 - open_ts) / 60000)
            if duration_min < 60:
                duration = f"{duration_min}m"
            else:
                duration = f"{duration_min // 60}h{duration_min % 60}m"
        else:
            duration = "N/A"

        # 风险预警
        if pnl_pct <= -5:
            alert = "⚠️"
        elif pnl_pct >= 3:
            alert = "✨"
        else:
            alert = ""

        lines.append(f"  {direction} {pair} {leverage}x: {pnl:+.1f} ({pnl_pct:+.1f}%) {duration} {alert}")
else:
    lines.append("📊 无持仓")

# === 策略统计 ===
trade_count = profit.get('trade_count', 0)
closed_count = profit.get('closed_trade_count', 0)
winrate = profit.get('winrate', 0) * 100  # API 返回 0~1 比例，转为百分比
max_dd = profit.get('max_drawdown', 0) * 100  # 同上

stats = []
if closed_count > 0:
    stats.append(f"胜率{winrate:.0f}%")
if max_dd > 0:
    stats.append(f"回撤{max_dd:.1f}%")
stats.append(f"交易{closed_count}/{trade_count}")

if stats:
    lines.append(f"📈 {' | '.join(stats)}")

# === 资金使用 ===
if total_stake > 0:
    usage_pct = ((total_stake - free_stake) / total_stake) * 100
    lines.append(f"💰 资金: {free_stake:.0f}/{total_stake:.0f} ({usage_pct:.0f}%占用)")

print("\\\\n".join(lines))
PYREPORT
)

    # 检查是否需要发送通知
    CURRENT_STATE=$(python3 << PYSTATE
import json

with open("$TMPDIR/profit.json") as f:
    profit = json.load(f)
with open("$TMPDIR/status.json") as f:
    status = json.load(f)

state = {
    "trade_count": profit.get('trade_count', 0),
    "position_count": len(status) if isinstance(status, list) else 0,
    "profit_pct": round(profit.get('profit_all_percent', 0), 1)
}
print(json.dumps(state))
PYSTATE
)

    # 清理临时文件
    rm -rf "$TMPDIR"

    SHOULD_NOTIFY="false"

    if [ -f "$CACHE_FILE" ]; then
        CACHED=$(cat "$CACHE_FILE")

        SHOULD_NOTIFY=$(python3 << PYCOMPARE
import json
from datetime import datetime

current = json.loads('''$CURRENT_STATE''')
cached = json.loads('''$CACHED''')

# 通知条件：
# 1. 交易次数变化
# 2. 持仓数变化
# 3. 收益变化超过 0.5%
# 4. 距离上次通知超过 1 小时（定时汇报）
trade_changed = current['trade_count'] != cached.get('trade_count', -1)
position_changed = current['position_count'] != cached.get('position_count', -1)
profit_changed = abs(current['profit_pct'] - cached.get('profit_pct', 0)) >= 0.5

# 检查是否超过 1 小时未通知
last_notify = cached.get('last_notify_at', '')
time_to_report = False
if last_notify:
    try:
        last_dt = datetime.fromisoformat(last_notify)
        hours_passed = (datetime.now(last_dt.tzinfo) - last_dt).total_seconds() / 3600
        time_to_report = hours_passed >= 1
    except:
        time_to_report = True
else:
    time_to_report = True

if trade_changed or position_changed or profit_changed or time_to_report:
    print("true")
else:
    print("false")
PYCOMPARE
)
    else
        SHOULD_NOTIFY="true"
    fi

    if [ "$SHOULD_NOTIFY" = "true" ]; then
        # 更新缓存（包含通知时间）
        echo "$CURRENT_STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); d['checked_at']='$(date -Iseconds)'; d['last_notify_at']='$(date -Iseconds)'; print(json.dumps(d))" > "$CACHE_FILE"
        output_notification "success" "Trading Monitor" "$REPORT"
        echo "$(date): 已发送通知"
    else
        # 更新缓存（保留之前的 last_notify_at）
        python3 << PYUPDATE > "$CACHE_FILE"
import json
current = json.loads('''$CURRENT_STATE''')
cached = json.loads('''$CACHED''')
current['checked_at'] = '$(date -Iseconds)'
# 保留之前的通知时间
if 'last_notify_at' in cached:
    current['last_notify_at'] = cached['last_notify_at']
print(json.dumps(current))
PYUPDATE
        echo "$(date): 无显著变化，跳过通知"
    fi
}

main "$@"
