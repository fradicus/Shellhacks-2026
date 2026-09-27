#!/usr/bin/env bash
# Start (or restart) a GridBridge dev server.
#   scripts/dev.sh [port] [atlas|local] [checkout-dir]
#   scripts/dev.sh                   -> port 3100, Atlas, this checkout
#   scripts/dev.sh 3200 local        -> port 3200, the local Docker Mongo (offline fallback)
#   scripts/dev.sh 3100 atlas /path/to/another/worktree
# Atlas reads MONGODB_URI_RO and MONGODB_DB from the repo-root .env (gitignored). Nothing is printed or written.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-3100}"
db="${2:-atlas}"
dir="${3:-$here}"
log="${TMPDIR:-/tmp}/gridbridge-dev-$port.log"

val() { grep -E "^$1=" "$here/.env" 2>/dev/null | head -1 | cut -d= -f2- || true; }

case "$db" in
  atlas)
    uri="$(val MONGODB_URI_RO)"
    name="$(val MONGODB_DB)"
    [ -n "$uri" ] || { echo "MONGODB_URI_RO is empty in $here/.env" >&2; exit 1; }
    ;;
  local)
    uri="mongodb://127.0.0.1:27018"
    name="gridbridge"
    docker start gridbridge-mongo >/dev/null 2>&1 || echo "warning: couldn't start the gridbridge-mongo container" >&2
    ;;
  *) echo "second argument must be atlas or local" >&2; exit 1 ;;
esac
name="${name:-gridbridge}"

# Stop whatever is serving this port.
if pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null)" && [ -n "$pids" ]; then
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 20); do lsof -t -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 0.5; done
fi

cd "$dir/web"
MONGODB_URI_RO="$uri" MONGODB_DB="$name" PORT="$port" nohup npx next dev -p "$port" >"$log" 2>&1 &
pid=$!
echo "Starting on http://localhost:$port ($db, $(git -C "$dir" log --oneline -1 | cut -c1-60)); log: $log"
for _ in $(seq 1 60); do
  code="$(curl -s -o /dev/null --max-time 60 -w '%{http_code}' "http://localhost:$port/" || true)"
  [ "$code" = "200" ] && { echo "Up."; exit 0; }
  # Next exits at once if this checkout already runs a dev server (one per directory): say why.
  kill -0 "$pid" 2>/dev/null || { echo "The server exited:" >&2; tail -6 "$log" >&2; exit 1; }
  sleep 2
done
echo "Not answering yet; check $log" >&2
exit 1
