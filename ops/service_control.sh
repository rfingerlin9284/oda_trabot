#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/rfing/ODA_TRABOT"
STATE_ENV="$REPO_ROOT/state/runtime.env"
SERVICE_NAME="oda_trabot.service"

write_mode() {
  local allow_orders="$1"
  cat > "$STATE_ENV" <<EOF
ODA_TRABOT_LOOP_SECONDS=60
ODA_TRABOT_ALLOW_PAPER_ORDERS=$allow_orders
ODA_TRABOT_CARTRIDGE_ROUTING=auto
ODA_TRABOT_PAPER_DATA_MODE=YES
ODA_TRABOT_DAY_SCALP_MIN_VOTES=2
ODA_TRABOT_DAY_SCALP_MIN_CONFIDENCE=0.68
ODA_TRABOT_EARLY_LONDON_SCALP_MIN_CONFIDENCE=0.66
EOF
}

show_status() {
  echo "ODA_TRABOT service status"
  echo
  systemctl --user status "$SERVICE_NAME" --no-pager || true
  echo
  echo "Runtime mode file:"
  cat "$STATE_ENV"
  echo
  if [[ -f "$REPO_ROOT/state/last_runtime_status.json" ]]; then
    echo "Last runtime status:"
    cat "$REPO_ROOT/state/last_runtime_status.json"
  else
    echo "No runtime status file yet."
  fi
}

case "${1:-}" in
  start-preview)
    write_mode "NO"
    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME"
    echo "ODA_TRABOT started in preview mode."
    ;;
  start-paper)
    write_mode "YES"
    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME"
    echo "ODA_TRABOT started in live paper mode."
    ;;
  restart-preview)
    write_mode "NO"
    systemctl --user daemon-reload
    systemctl --user restart "$SERVICE_NAME"
    echo "ODA_TRABOT restarted in preview mode."
    ;;
  restart-paper)
    write_mode "YES"
    systemctl --user daemon-reload
    systemctl --user restart "$SERVICE_NAME"
    echo "ODA_TRABOT restarted in live paper mode."
    ;;
  stop)
    systemctl --user stop "$SERVICE_NAME"
    echo "ODA_TRABOT stopped."
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: $0 {start-preview|start-paper|restart-preview|restart-paper|stop|status}" >&2
    exit 1
    ;;
esac
