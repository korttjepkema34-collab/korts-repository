#!/bin/sh
# Reviewed deployment helper for the Tjepkema Server WSL host. This script is intentionally not
# run by tests or setup. Run only after the owner approves the reviewed commit.
set -eu

SOURCE=/srv/my-assistant/source
RUNTIME=/srv/my-assistant/runtime
DASHBOARD=/srv/dashboard
TAILSCALE_IP=100.72.202.38
EXPECTED_REV=${1:-}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo sh scripts/deploy-dashboard-wsl.sh <approved-commit>" >&2
  exit 2
fi
if [ -z "$EXPECTED_REV" ]; then
  echo "Pass the exact owner-approved commit hash." >&2
  exit 2
fi

cd "$SOURCE"
ACTUAL_REV=$(git rev-parse HEAD)
case "$ACTUAL_REV" in "$EXPECTED_REV"*) ;; *)
  echo "Refusing: checkout is $ACTUAL_REV, expected $EXPECTED_REV" >&2; exit 2;;
esac
if [ -n "$(git status --porcelain)" ]; then
  echo "Refusing: server source checkout has uncommitted changes." >&2
  exit 2
fi

# Prove the exact server checkout before changing services.
python3 -m unittest discover -s tests/assistant -q
python3 -m compileall -q assistant scripts tests/assistant
python3 scripts/check_private_leak.py
python3 scripts/synthetic_e2e.py

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/srv/my-assistant/deploy-backups/$STAMP
mkdir -p "$BACKUP"
cp -a /etc/systemd/system/my-assistant.service "$BACKUP/my-assistant.service" 2>/dev/null || true
cp -a /etc/systemd/system/my-assistant-runner.service "$BACKUP/my-assistant-runner.service" 2>/dev/null || true
cp -a "$DASHBOARD/default.conf" "$BACKUP/default.conf"
cp -a "$DASHBOARD/html/assistant.html" "$BACKUP/assistant.html" 2>/dev/null || true

sudo -u kortt env ASSISTANT_HOME="$RUNTIME" python3 -m assistant.run init
sudo -u kortt env ASSISTANT_HOME="$RUNTIME" python3 -m assistant.web bind "$TAILSCALE_IP" --port 8772
sudo -u kortt env ASSISTANT_HOME="$RUNTIME" python3 -m assistant.web access open --user kort

# Allow same-origin requests from the established Tjepkema Server names. Password hashes and
# provider credentials remain in the private runtime/.env and never enter this script or Git.
sudo -u kortt env ASSISTANT_HOME="$RUNTIME" python3 -c '
from assistant.web import load_config, save_config
c = load_config()
c["extra_origins"] = ["http://192.168.1.73", "http://tjepkema_server", "http://100.72.202.38"]
save_config(c)
'

install -m 0644 deploy/my-assistant-dashboard.service /etc/systemd/system/my-assistant.service
install -m 0644 deploy/my-assistant-runner.service /etc/systemd/system/my-assistant-runner.service
install -m 0644 deploy/tjepkema-dashboard.conf "$DASHBOARD/default.conf"
systemctl daemon-reload
systemctl enable --now my-assistant.service my-assistant-runner.service
docker exec dashboard nginx -t
docker exec dashboard nginx -s reload

sleep 2
systemctl is-active --quiet my-assistant.service
systemctl is-active --quiet my-assistant-runner.service
curl -fsS "http://$TAILSCALE_IP:8772/" | grep -q "Kort's Assistant"
curl -fsS -H 'Host: 192.168.1.73' http://127.0.0.1/assistant/ | grep -q "Kort's Assistant"
curl -fsS -H 'Host: 192.168.1.73' http://127.0.0.1/assistant/static/app.js | grep -q 'SIMULATED PREVIEW\|previewBubble'

echo "Deployment checks passed. Backup: $BACKUP"
echo "Open http://192.168.1.73/ and choose My Assistant."
echo "Rollback files are preserved in $BACKUP; source remains pinned to $ACTUAL_REV."
