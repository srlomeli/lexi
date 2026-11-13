#!/usr/bin/env bash
# Turn the public site https://lexi.salvadorlomeli.com on and off.
#   ./deploy/lexi.sh on      start Rasa, the page and the tunnel in the background
#   ./deploy/lexi.sh off     take the site offline
#   ./deploy/lexi.sh status  show what is running
#   ./deploy/lexi.sh logs    show recent log lines
set -uo pipefail

cd "$(dirname "$0")/.."
URL="https://lexi.salvadorlomeli.com"
RUN="deploy/run"
RASA="${RASA:-.venv/bin/rasa}"
TUNNEL_CMD="cloudflared tunnel --config deploy/cloudflared.yml run lexi"
PAGE_CMD="http.server 8080"
mkdir -p "$RUN"

rasa_up()   { curl -s -m 2 http://localhost:5005/ >/dev/null; }
page_up()   { curl -s -m 2 http://localhost:8080/ >/dev/null; }
tunnel_up() { pgrep -f "$TUNNEL_CMD" >/dev/null; }
site_up()   { [ "$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$URL/")" = "200" ]; }

say_state() { if "$2"; then printf '  %-8s running\n' "$1"; else printf '  %-8s stopped\n' "$1"; fi; }

cmd_on() {
  if rasa_up; then
    echo "Rasa is already running on port 5005."
  else
    echo "Starting Rasa (this can take a minute)..."
    nohup "$RASA" run --cors "*" >"$RUN/rasa.log" 2>&1 &
    echo $! >"$RUN/rasa.pid"
    for _ in $(seq 1 90); do rasa_up && break; sleep 2; done
    rasa_up || { echo "Rasa didn't start. See: ./deploy/lexi.sh logs"; exit 1; }
  fi

  if page_up; then
    echo "The page server is already running on port 8080."
  else
    echo "Starting the page server..."
    nohup python3 -m http.server 8080 --bind 127.0.0.1 --directory web >"$RUN/page.log" 2>&1 &
    echo $! >"$RUN/page.pid"
  fi

  if tunnel_up; then
    echo "The tunnel is already running."
  else
    echo "Opening the tunnel..."
    nohup $TUNNEL_CMD >"$RUN/tunnel.log" 2>&1 &
    echo $! >"$RUN/tunnel.pid"
  fi

  for _ in $(seq 1 15); do site_up && break; sleep 2; done
  if site_up; then echo "Live at $URL"; else echo "Started, but $URL isn't answering yet. Try: ./deploy/lexi.sh status"; fi
}

cmd_off() {
  pkill -f "$TUNNEL_CMD" && echo "Tunnel stopped." || echo "Tunnel wasn't running."
  pkill -f "$PAGE_CMD" && echo "Page server stopped." || echo "Page server wasn't running."
  if [ -f "$RUN/rasa.pid" ] && kill "$(cat "$RUN/rasa.pid")" 2>/dev/null; then
    echo "Rasa stopped."
  elif rasa_up; then
    echo "Rasa left running (you started it yourself)."
  fi
  rm -f "$RUN"/*.pid
  echo "Offline: $URL"
}

cmd_status() {
  say_state "Rasa" rasa_up
  say_state "Page" page_up
  say_state "Tunnel" tunnel_up
  if site_up; then echo "  Site     UP at $URL"; else echo "  Site     DOWN"; fi
}

cmd_logs() {
  for f in rasa page tunnel; do
    [ -f "$RUN/$f.log" ] && { echo "== $f =="; tail -n 15 "$RUN/$f.log"; }
  done
  return 0
}

case "${1:-}" in
  on) cmd_on ;;
  off) cmd_off ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  *) echo "Usage: ./deploy/lexi.sh on | off | status | logs"; exit 1 ;;
esac
