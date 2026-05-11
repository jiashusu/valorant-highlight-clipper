#!/bin/zsh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="8787"
HOST="127.0.0.1"
URL="http://${HOST}:${PORT}"
PID_FILE="${PROJECT_DIR}/.valorant_clipper.pid"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/valorant_clipper.log"
PYTHON="${PROJECT_DIR}/.venv/bin/python"

choose_action() {
  /usr/bin/osascript -e 'choose from list {"启动", "关闭", "重新启动", "查看当前状态"} with title "Valorant 高光剪辑" with prompt "请选择操作" OK button name "执行" cancel button name "取消"'
}

notify() {
  if [ "${VALORANT_CLIPPER_PLAIN:-}" = "1" ]; then
    print -r -- "$1"
    return 0
  fi
  /usr/bin/osascript - "$1" <<'APPLESCRIPT'
on run argv
  display dialog (item 1 of argv) with title "Valorant 高光剪辑" buttons {"OK"} default button "OK"
end run
APPLESCRIPT
}

find_pid() {
  if [ -f "$PID_FILE" ]; then
    local saved_pid
    saved_pid="$(cat "$PID_FILE" 2>/dev/null)"
    if [ -n "$saved_pid" ] && kill -0 "$saved_pid" 2>/dev/null; then
      echo "$saved_pid"
      return 0
    fi
    rm -f "$PID_FILE"
  fi

  local port_pid
  port_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1)"
  if [ -n "$port_pid" ]; then
    echo "$port_pid"
    return 0
  fi
  return 1
}

ensure_environment() {
  cd "$PROJECT_DIR" || exit 1
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi

  if ! "$PYTHON" - <<'PY'
missing = []
for module in ("fastapi", "uvicorn", "numpy", "PIL"):
    try:
        __import__(module)
    except Exception:
        missing.append(module)
if missing:
    raise SystemExit(1)
PY
  then
    "$PYTHON" -m pip install -r requirements.txt
  fi
}

status_message() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    echo "当前状态：运行中
PID：${pid}
地址：${URL}
日志：${LOG_FILE}"
  else
    echo "当前状态：未运行
地址：${URL}
日志：${LOG_FILE}"
  fi
}

start_server() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    open "$URL"
    notify "已经在运行。
PID：${pid}
已打开：${URL}"
    return 0
  fi

  ensure_environment
  mkdir -p "$LOG_DIR"
  cd "$PROJECT_DIR" || exit 1

  PYTHONPATH="${PROJECT_DIR}/src" nohup "$PYTHON" -m uvicorn valorant_clipper.web_app:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
  local new_pid="$!"
  echo "$new_pid" > "$PID_FILE"

  for _ in {1..20}; do
    if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      open "$URL"
      notify "启动成功。
PID：${new_pid}
已打开：${URL}"
      return 0
    fi
    sleep 0.3
  done

  notify "启动可能失败，请查看日志：
${LOG_FILE}"
  return 1
}

stop_server() {
  local pid
  pid="$(find_pid)"
  if [ -z "$pid" ]; then
    notify "当前没有运行中的服务。"
    return 0
  fi

  kill "$pid" 2>/dev/null
  for _ in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      notify "已关闭服务。
PID：${pid}"
      return 0
    fi
    sleep 0.2
  done

  kill -9 "$pid" 2>/dev/null
  rm -f "$PID_FILE"
  notify "已强制关闭服务。
PID：${pid}"
}

restart_server() {
  local pid
  pid="$(find_pid)"
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null
    sleep 0.8
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null
    fi
    rm -f "$PID_FILE"
  fi
  start_server
}

main() {
  local action
  case "${1:-}" in
    start)
      action="启动"
      ;;
    stop)
      action="关闭"
      ;;
    restart)
      action="重新启动"
      ;;
    status)
      action="查看当前状态"
      ;;
    "")
      action="$(choose_action)"
      ;;
    *)
      action="${1:-}"
      ;;
  esac
  if [ "$action" = "false" ] || [ -z "$action" ]; then
    exit 0
  fi

  case "$action" in
    "启动")
      start_server
      ;;
    "关闭")
      stop_server
      ;;
    "重新启动")
      restart_server
      ;;
    "查看当前状态")
      notify "$(status_message)"
      ;;
    *)
      notify "未知操作：${action}"
      ;;
  esac
}

main "${1:-}"
