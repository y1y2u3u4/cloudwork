#!/bin/bash
# CloudWork Cloudflare Tunnel 启动脚本
# 用法: ./scripts/start-tunnel.sh [start|stop|status]

CLOUDFLARED=~/bin/cloudflared
TOKEN="eyJhIjoiOGMwZTY2ZTVkM2IxNGYwOTc0MTIwZmY5NjM4ZThmYzUiLCJ0IjoiOTYyMzEwNWQtYjdlNC00ZTlhLWJkNDMtNzk2OTRiYWE0MzczIiwicyI6IlpETXdZelU0WlRZdE5qSTBZaTAwWkRGakxXRmtNemd0WkdZMk1tWm1OemxoWXprdyJ9"
LOGFILE=/tmp/cloudflared.log
PIDFILE=/tmp/cloudflared.pid

start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
        echo "Tunnel 已在运行 (PID: $(cat $PIDFILE))"
        return 0
    fi
    echo "启动 Cloudflare Tunnel..."
    $CLOUDFLARED tunnel --no-autoupdate run --token "$TOKEN" > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 3
    if kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
        echo "Tunnel 已启动 (PID: $(cat $PIDFILE))"
        grep "Registered tunnel connection" "$LOGFILE" | tail -4
    else
        echo "启动失败，查看日志: $LOGFILE"
        tail -10 "$LOGFILE"
        return 1
    fi
}

stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "Tunnel 已停止 (PID: $PID)"
        else
            echo "进程 $PID 已不存在"
        fi
        rm -f "$PIDFILE"
    else
        # 尝试通过 pgrep 查找
        PID=$(pgrep -f "cloudflared.*tunnel.*run")
        if [ -n "$PID" ]; then
            kill "$PID"
            echo "Tunnel 已停止 (PID: $PID)"
        else
            echo "Tunnel 未在运行"
        fi
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
        echo "Tunnel 运行中 (PID: $(cat $PIDFILE))"
        grep "Registered tunnel connection" "$LOGFILE" 2>/dev/null | tail -4
    else
        PID=$(pgrep -f "cloudflared.*tunnel.*run")
        if [ -n "$PID" ]; then
            echo "Tunnel 运行中 (PID: $PID, 无 pidfile)"
        else
            echo "Tunnel 未运行"
        fi
    fi
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    restart) stop; sleep 2; start ;;
    *) echo "用法: $0 {start|stop|status|restart}" ;;
esac
