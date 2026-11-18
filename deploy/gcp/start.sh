#!/usr/bin/env bash
# Start Rasa and the page/proxy server, then (if credentials are mounted) the
# Cloudflare Tunnel. The tunnel waits until Rasa answers, so visitors never
# reach a half-started game after a deploy or reboot.
set -euo pipefail
cd /home/user/app

# Rasa Pro reads RASA_PRO_LICENSE; the project's .env calls it RASA_LICENSE.
export RASA_PRO_LICENSE="${RASA_PRO_LICENSE:-${RASA_LICENSE:-}}"

caddy run --config Caddyfile --adapter caddyfile &

MODEL="$(ls -t models/*.tar.gz | head -1)"
rasa run --model "$MODEL" --cors "*" --port 5005 --interface 127.0.0.1 &
RASA_PID=$!

echo "Waiting for Rasa before opening the tunnel..."
until curl -s -m 2 -o /dev/null http://127.0.0.1:5005/; do
  kill -0 "$RASA_PID" 2>/dev/null || { echo "Rasa exited during startup."; exit 1; }
  sleep 2
done
echo "Rasa is ready."

CREDS=/run/secrets/cf-creds.json
if [ -f "$CREDS" ]; then
  cat > /tmp/cloudflared.yml <<CFG
tunnel: lexi
credentials-file: $CREDS
ingress:
  - hostname: lexi.salvadorlomeli.com
    service: http://localhost:7860
  - service: http_status:404
CFG
  cloudflared tunnel --no-autoupdate --config /tmp/cloudflared.yml run lexi &
else
  echo "No tunnel credentials at $CREDS: skipping the tunnel."
fi

# Keep the container alive as long as Rasa runs; if it dies, Docker restarts us.
wait "$RASA_PID"
