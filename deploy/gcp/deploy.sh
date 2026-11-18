#!/usr/bin/env bash
# Deploy Lexi's Word Game to a Google Cloud VM.  See deploy/gcp/README.md.
set -euo pipefail

cd "$(dirname "$0")/../.."
PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM="${GCP_VM:-lexi}"
MACHINE="${GCP_MACHINE:-e2-medium}"
CREDS="$HOME/.cloudflared/$(sed -n 's#^credentials-file: .*/\([^/]*\.json\)$#\1#p' deploy/cloudflared.yml)"
G=(--project "$PROJECT" --zone "$ZONE")

[ -n "$PROJECT" ] || { echo "Set GCP_PROJECT or run: gcloud config set project <id>"; exit 1; }
remote() { gcloud compute ssh "$VM" "${G[@]}" --command "$1"; }

case "${1:-deploy}" in
  logs)  remote "sudo docker logs -f --tail 100 lexi"; exit ;;
  stop)  gcloud compute instances stop "$VM" "${G[@]}"; exit ;;
  start) gcloud compute instances start "$VM" "${G[@]}"; exit ;;
  deploy) ;;
  *) echo "Usage: deploy.sh [deploy|logs|stop|start]"; exit 1 ;;
esac

[ -f .env ] || { echo "Missing .env"; exit 1; }
[ -f "$CREDS" ] || { echo "Missing tunnel credentials: $CREDS"; exit 1; }

if ! gcloud compute instances describe "$VM" "${G[@]}" >/dev/null 2>&1; then
  echo "Creating VM $VM ($MACHINE) in $ZONE..."
  gcloud services enable compute.googleapis.com --project "$PROJECT"
  gcloud compute instances create "$VM" "${G[@]}" \
    --machine-type "$MACHINE" --image-family debian-12 --image-project debian-cloud \
    --boot-disk-size 20GB \
    --metadata startup-script='#!/bin/bash
command -v docker >/dev/null || { apt-get update && apt-get install -y docker.io && systemctl enable --now docker; }'
  echo "Waiting for Docker on the VM..."
  for _ in $(seq 1 40); do remote "command -v docker" >/dev/null 2>&1 && break; sleep 10; done
fi

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/app/models" "$STAGE/secrets"
cp deploy/gcp/{Dockerfile,Caddyfile,start.sh} "$STAGE/app/"
cp -R actions channels domain game prompts web "$STAGE/app/"
cp config.yml endpoints.yml credentials.yml "$STAGE/app/"
cp "$(ls -t models/*.tar.gz | head -1)" "$STAGE/app/models/"
find "$STAGE/app" -name __pycache__ -prune -exec rm -rf {} +
# docker --env-file keeps quotes literally, so strip KEY="value" quotes.
sed -E -e "s/^([A-Za-z_][A-Za-z0-9_]*)=\"(.*)\"[[:space:]]*$/\1=\2/" \
       -e "s/^([A-Za-z_][A-Za-z0-9_]*)='(.*)'[[:space:]]*$/\1=\2/" .env > "$STAGE/secrets/env"
cp "$CREDS" "$STAGE/secrets/cf-creds.json"

echo "Copying files to the VM..."
remote "rm -rf ~/lexi && mkdir -p ~/lexi"
gcloud compute scp --recurse "${G[@]}" "$STAGE/app" "$STAGE/secrets" "$VM:~/lexi/"

echo "Building and starting the container (first build takes several minutes)..."
remote 'set -e
cd ~/lexi
chmod 600 secrets/env; chmod 644 secrets/cf-creds.json
sudo docker build -t lexi app
sudo docker rm -f lexi >/dev/null 2>&1 || true
sudo docker run -d --name lexi --restart unless-stopped \
  --env-file secrets/env -v "$PWD/secrets/cf-creds.json:/run/secrets/cf-creds.json:ro" lexi'
echo "Started. Follow startup with: ./deploy/gcp/deploy.sh logs"
