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
  kill -0 "$pid" 2>/dev/null || return 1

  # A stale PID file must not block recovery merely because Linux reused its PID.
  # Accept only a process that still looks like the configured Actions runner.
  local cmdline
  cmdline="$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null || true)"
  [[ "$cmdline" == *"Runner.Listener"* || "$cmdline" == *"$ROOT"* ]]
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

systemd_user_is_ready() {
  command -v systemctl >/dev/null 2>&1 || return 1
  systemctl --user show-environment >/dev/null 2>&1
}

install_service() {
  preflight

  if ! systemd_user_is_ready; then
    echo "USER_SYSTEMD_UNAVAILABLE" >&2
    echo "The user systemd manager is not reachable; do not register a replacement runner." >&2
    return 4
  fi

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
  if systemd_user_is_ready; then
    systemctl --user show "$SERVICE_NAME" \
      -p LoadState -p ActiveState -p SubState -p MainPID -p FragmentPath \
      --no-pager || true
  else
    echo "USER_SYSTEMD_UNAVAILABLE"
  fi

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

doctor_service() {
  local rc=0

  echo "== doctor: prerequisites =="
  if preflight; then
    echo "PREFLIGHT=ready"
  else
    rc=$?
    echo "PREFLIGHT=failed code=$rc"
    return "$rc"
  fi

  echo
  echo "== doctor: user systemd =="
  if systemd_user_is_ready; then
    echo "USER_SYSTEMD=ready"
  else
    echo "USER_SYSTEMD=unavailable"
    return 4
  fi

  echo
  echo "== doctor: listener ownership =="
  local managed="inactive"
  if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    managed="active"
  fi

  if manual_listener_is_live; then
    local pid
    pid="$(manual_pid)"
    echo "MANUAL_LISTENER=live pid=$pid"
    echo "MANAGED_LISTENER=$managed"
    if [[ "$managed" == "active" ]]; then
      echo "DOCTOR=duplicate-listeners"
      return 5
    fi
    echo "DOCTOR=manual-listener-live"
    echo "NEXT=stop only pid $pid gracefully, then run: bash tools/runner-service.sh install"
    return 3
  fi

  echo "MANUAL_LISTENER=absent"
  echo "MANAGED_LISTENER=$managed"
  if [[ "$managed" == "active" ]]; then
    echo "DOCTOR=ready"
    return 0
  fi

  echo "DOCTOR=no-live-listener"
  if [[ -f "$UNIT_DEST" ]]; then
    echo "NEXT=bash tools/runner-service.sh restart"
  else
    echo "NEXT=bash tools/runner-service.sh install"
  fi
  return 4
}

restart_service() {
  preflight
  if ! systemd_user_is_ready; then
    echo "USER_SYSTEMD_UNAVAILABLE" >&2
    return 4
  fi
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
  doctor)
    doctor_service
    ;;
  restart)
    restart_service
    ;;
  logs)
    exec journalctl --user -u "$SERVICE_NAME" -n "${2:-100}" --no-pager
    ;;
  *)
    echo "usage: $0 {doctor|install|status|restart|logs [lines]}" >&2
    exit 2
    ;;
esac
