#!/usr/bin/env bash
set -euo pipefail

EXECUTE=0
if [ "${1:-}" = "--execute" ] && [ "$#" -eq 1 ]; then
  EXECUTE=1
elif [ "$#" -ne 0 ]; then
  printf 'usage: %s [--execute]\n' "$0" >&2
  exit 2
fi

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUNNER="$REPO_ROOT/scripts/sync-apple-design.py"
PYTHON=$(command -v python3 || true)
UNIT_NAME=apple-design-skill-update
UNIT_ROOT=${XDG_CONFIG_HOME:-"$HOME/.config"}/systemd/user
SERVICE="$UNIT_ROOT/$UNIT_NAME.service"
TIMER="$UNIT_ROOT/$UNIT_NAME.timer"

printf '%s\n' 'APPLE_DESIGN_TIMER operation=register mode=Check'
printf 'service=%s\ntimer=%s\n' "$SERVICE" "$TIMER"
printf '%s\n' 'schedule=daily@06:30 Asia/Singapore, Persistent=true'
printf '%s\n' 'scopes=WSL Codex, WSL Claude, Windows Codex, Windows Claude'
printf '%s\n' 'apply=never-scheduled; logs=systemd-user-journal'

if [ "$EXECUTE" -ne 1 ]; then
  printf '%s\n' 'APPLE_DESIGN_TIMER status=preview-only'
  exit 0
fi

[ -n "$PYTHON" ] || {
  printf '%s\n' 'python3 is required for the Apple Design updater' >&2
  exit 2
}
[ -f "$RUNNER" ] || {
  printf 'Apple Design updater not found: %s\n' "$RUNNER" >&2
  exit 2
}
command -v systemctl >/dev/null 2>&1 || {
  printf '%s\n' 'systemctl is required for the user timer' >&2
  exit 2
}

mkdir -p "$UNIT_ROOT"
escaped_repo=${REPO_ROOT//\\/\\\\}
escaped_repo=${escaped_repo//\"/\\\"}
escaped_runner=${RUNNER//\\/\\\\}
escaped_runner=${escaped_runner//\"/\\\"}
escaped_python=${PYTHON//\\/\\\\}
escaped_python=${escaped_python//\"/\\\"}
service_tmp="$SERVICE.tmp.$$"
timer_tmp="$TIMER.tmp.$$"
trap 'rm -f -- "$service_tmp" "$timer_tmp"' EXIT

cat >"$service_tmp" <<EOF
[Unit]
Description=Check published Apple Design skill snapshots
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory="$escaped_repo"
ExecStart="$escaped_python" "$escaped_runner" --mode Check
SuccessExitStatus=3
TimeoutStartSec=5min
EOF

cat >"$timer_tmp" <<EOF
[Unit]
Description=Schedule published Apple Design skill checks

[Timer]
OnCalendar=*-*-* 06:30:00 Asia/Singapore
Persistent=true
Unit=$UNIT_NAME.service

[Install]
WantedBy=timers.target
EOF

mv -f -- "$service_tmp" "$SERVICE"
mv -f -- "$timer_tmp" "$TIMER"
systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME.timer"
printf 'APPLE_DESIGN_TIMER status=registered timer=%s.timer mode=Check\n' "$UNIT_NAME"
