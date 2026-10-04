#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-7860}"

LOG="$ROOT/.local/app.log"
PID_FILE="$ROOT/.local/app.pid"
mkdir -p "$ROOT/.local"

pid_of() { cat "$PID_FILE" 2>/dev/null || true; }
running() { local p; p="$(pid_of)"; [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; }
listening() { lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; }

pick_python() {
  for c in "$ROOT/.venv/bin/python" "$ROOT/venv/bin/python"; do
    [[ -x "$c" ]] && { echo "$c"; return; }
  done
  command -v python3 || true
}

ensure_web() {
  [[ -d "$ROOT/web/dist" ]] && return 0
  echo "• 首次运行，构建前端 (web/dist)…"
  npm --prefix "$ROOT/web" install || return 1
  npm --prefix "$ROOT/web" run build || return 1
}

start() {
  if running; then
    echo "• 已在运行 (pid $(pid_of)) → http://$HOST:$PORT"
    return
  fi
  if listening; then
    echo "✗ 端口 $PORT 已被占用（可改用 PORT=7861 npm run up）"
    return 1
  fi
  local python; python="$(pick_python)"
  if [[ -z "$python" ]]; then
    echo "✗ 未找到 Python，请先安装 Python 3.8+ 或创建虚拟环境"
    return 1
  fi
  ensure_web || { echo "✗ 前端构建失败"; return 1; }
  ( cd "$ROOT" && exec "$python" -m uvicorn server:app --host "$HOST" --port "$PORT" ) >"$LOG" 2>&1 &
  echo $! >"$PID_FILE"
  for _ in $(seq 1 50); do
    listening && { echo "▶ 已启动 (pid $(pid_of)) → http://$HOST:$PORT"; return; }
    kill -0 "$(pid_of)" 2>/dev/null || { echo "✗ 启动失败，日志：$LOG"; tail -n 15 "$LOG"; return 1; }
    sleep 0.2
  done
  echo "⚠ 端口未就绪，日志：$LOG"
}

stop() {
  local p; p="$(pid_of)"
  if [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; then
    kill "$p" 2>/dev/null
    for _ in $(seq 1 25); do kill -0 "$p" 2>/dev/null || break; sleep 0.2; done
    kill -0 "$p" 2>/dev/null && kill -9 "$p" 2>/dev/null
    echo "■ 已停止 (pid $p)"
  else
    echo "• 未运行"
  fi
  rm -f "$PID_FILE"
  listening && echo "• 端口 $PORT 仍被占用（可能是外部启动的进程）"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  *) echo "用法: $0 {start|stop}" ;;
esac
