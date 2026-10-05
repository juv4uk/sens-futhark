#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="actions-runner-sens-futhark.service"
ROOT="${SENS_FUTHARK_RUNNER_ROOT:-$HOME/gpu-runners/sens-futhark}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="$REPO_ROOT/systemd/$SERVICE_NAME"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_DEST="$UNIT_DIR/$SERVICE_NAME"
MANUAL_PID_FILE="$ROOT/.manual-runner.pid"

manual_pid() {
  [[ -f "$MANUAL_PID_FILE" ]] || return 1
  local pid
  pid="$(tr -d '[:space:]' <"$MANUAL_PID_FILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$pid"
}

manual_listener_is_live() {
  local pid
  pid="$(manual_pid)" || return 1
  kill -0 "$pid" 2>/dev/null
}

preflight() {
  [[ -f "$ROOT/.runner" ]] || {
    echo "runner registration missing: $ROOT/.runner" >&2
    return 2
  }
  [[ -x "$ROOT/run.sh" ]] || {
    echo "runner launcher missing/not executable: $ROOT/run.sh" >&2
    return 2
  }
  [[ -f "$UNIT_SOURCE" ]] || {
    echo "unit source missing: $UNIT_SOURCE" >&2
    return 2
  }
}

install_service() {
  preflight

  if manual_listener_is_live; then
    local pid
    pid="$(manual_pid)"
    cat >&2 <<EOF
REFUSE_DUPLICATE_LISTENER pid=$pid
A manual sens-futhark listener is still alive.
Stop only that listener gracefully, then rerun:
  systemctl --user enable --now $SERVICE_NAME
Do not restart the whole WSL distribution.
EOF
    return 3
  fi

  mkdir -p "$UNIT_DIR"
  install -m 0644 "$UNIT_SOURCE" "$UNIT_DEST"
  systemctl --user daemon-reload
  systemctl --user enable --now "$SERVICE_NAME"
  status_service
}

status_service() {
  echo "== managed service =="
  systemctl --user show "$SERVICE_NAME" \
    -p LoadState -p ActiveState -p SubState -p MainPID -p FragmentPath \
    --no-pager || true

  echo
  echo "== manual listener =="
  if manual_listener_is_live; then
    echo "LIVE pid=$(manual_pid) source=$MANUAL_PID_FILE"
  elif [[ -f "$MANUAL_PID_FILE" ]]; then
    echo "STALE pid_file=$MANUAL_PID_FILE value=$(cat "$MANUAL_PID_FILE" 2>/dev/null || true)"
  else
    echo "ABSENT"
  fi

  echo
  echo "== runner registration =="
  if [[ -f "$ROOT/.runner" ]]; then
    python3 - "$ROOT/.runner" <<'PY'
import json, sys
p=sys.argv[1]
try:
    data=json.load(open(p, encoding="utf-8"))
except Exception as exc:
    print(f"unreadable registration: {exc}")
else:
    for key in ("agentName", "gitHubUrl", "workFolder"):
        if key in data:
            print(f"{key}={data[key]}")
PY
  else
    echo "missing $ROOT/.runner"
  fi

  echo
  echo "== latest runner diagnostic =="
  latest="$(find "$ROOT/_diag" -maxdepth 1 -type f -name 'Runner_*.log' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2- || true)"
  if [[ -n "$latest" ]]; then
    echo "file=$latest"
    tail -n 30 "$latest"
  else
    echo "no Runner_*.log found"
  fi
}

restart_service() {
  preflight
  if manual_listener_is_live; then
    echo "REFUSE_DUPLICATE_LISTENER pid=$(manual_pid)" >&2
    return 3
  fi
  systemctl --user restart "$SERVICE_NAME"
  status_service
}

case "${1:-}" in
  install)
    install_service
    ;;
  status)
    status_service
    ;;
  restart)
    restart_service
    ;;
  logs)
    exec journalctl --user -u "$SERVICE_NAME" -n "${2:-100}" --no-pager
    ;;
  *)
    echo "usage: $0 {install|status|restart|logs [lines]}" >&2
    exit 2
    ;;
esac
