# Google Cloud deployment

Runs the whole game on one Compute Engine VM so https://lexi.salvadorlomeli.com
stays up without a laptop.

The container (`Dockerfile`, `start.sh`, `Caddyfile`) runs Rasa Pro on 5005,
Caddy on 7860 (serves `web/` and forwards `/webhooks/` to Rasa), and the `lexi`
Cloudflare Tunnel pointed at Caddy.

    ./deploy/gcp/deploy.sh            # create the VM if needed, then build and (re)start
    ./deploy/gcp/deploy.sh logs       # follow the container logs
    ./deploy/gcp/deploy.sh stop       # stop the VM (stops billing for CPU/RAM)
    ./deploy/gcp/deploy.sh start      # start it again

Settings via environment variables: `GCP_PROJECT` (default: gcloud's current
project), `GCP_ZONE` (us-central1-a), `GCP_VM` (lexi), `GCP_MACHINE` (e2-medium).

Secrets never leave your laptop and the VM: `.env` and
`~/.cloudflared/<tunnel-id>.json` are copied to the VM over SSH and mounted
into the container. Only run one copy of the tunnel at a time
(`./deploy/lexi.sh off` on your laptop).
