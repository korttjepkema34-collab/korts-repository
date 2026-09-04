#!/usr/bin/env bash
# Linux equivalent of supervise.ps1.
root="$(cd "$(dirname "$0")/.." && pwd)"; cd "$root"
backoff=10
while true; do
  selfchange=0; [ -f RESTART_REQUESTED ] && { selfchange=1; rm -f RESTART_REQUESTED; }
  started=$(date +%s)
  set -a; [ -f server/.env ] && source server/.env; set +a
  REPO_ROOT="$root" PYTHONPATH="$root:$root/server" python3 -m orchestrator.main; code=$?
  ran=$(( $(date +%s) - started ))
  if [ "$code" = "3" ]; then echo "supervisor: restart requested"; backoff=5; continue; fi
  healthy=0; [ -f reports/health.json ] && [ $(( $(date +%s) - $(stat -c %Y reports/health.json) )) -lt 180 ] && healthy=1
  if [ "$selfchange" = "1" ] && [ "$ran" -lt 300 ] && [ "$healthy" = "0" ] && [ -f reports/last_good.txt ]; then
    sha=$(cat reports/last_good.txt); echo "supervisor: rolling back to $sha"
    git checkout -q main; git revert --no-edit -m 1 HEAD 2>/dev/null || git reset -q --hard "$sha"
    echo "- $(date -Is): rolled back to $sha after a crash within 5 min of an engineer merge (exit $code)" >> incidents/ROLLBACKS.md
  fi
  echo "supervisor: exited $code after ${ran}s; restarting in ${backoff}s"; sleep "$backoff"
  backoff=$(( backoff * 2 )); [ "$backoff" -gt 300 ] && backoff=300; [ "$ran" -gt 600 ] && backoff=10
done
