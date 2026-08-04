#!/usr/bin/env bash
set -euo pipefail

EXECUTE=0
LINUX_ONLY=0
for argument in "$@"; do
  case "$argument" in
    --execute)
      [ "$EXECUTE" -eq 0 ] || {
        printf 'duplicate option: %s\n' "$argument" >&2
        exit 2
      }
      EXECUTE=1
      ;;
    --linux-only)
      [ "$LINUX_ONLY" -eq 0 ] || {
        printf 'duplicate option: %s\n' "$argument" >&2
        exit 2
      }
      LINUX_ONLY=1
      ;;
    *)
      printf 'usage: %s [--linux-only] [--execute]\n' "$0" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUNNER="$REPO_ROOT/scripts/sync-apple-design.py"
PYTHON=$(command -v python3 || true)
UNIT_NAME=apple-design-skill-update
UNIT_ROOT=${XDG_CONFIG_HOME:-"$HOME/.config"}/systemd/user
SERVICE="$UNIT_ROOT/$UNIT_NAME.service"
TIMER="$UNIT_ROOT/$UNIT_NAME.timer"

SCOPE_PROFILE=wsl
SCOPE_SUMMARY='WSL Codex, WSL Claude, Windows Codex, Windows Claude'
SERVICE_PROFILE_ARG=
if [ "$LINUX_ONLY" -eq 1 ]; then
  SCOPE_PROFILE=linux
  SCOPE_SUMMARY='Linux Codex, Linux Claude'
  SERVICE_PROFILE_ARG=' --scope-profile linux'
fi

printf 'APPLE_DESIGN_TIMER operation=register mode=Check scope_profile=%s\n' "$SCOPE_PROFILE"
printf 'service=%s\ntimer=%s\n' "$SERVICE" "$TIMER"
printf '%s\n' 'schedule=daily@06:30 Asia/Singapore, Persistent=true'
printf 'scopes=%s\n' "$SCOPE_SUMMARY"
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
WorkingDirectory=$escaped_repo
ExecStart="$escaped_python" "$escaped_runner" --mode Check$SERVICE_PROFILE_ARG
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
