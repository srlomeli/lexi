# Container for Lexi's Word Game (runs on a Google Cloud VM, see deploy.sh).
# Runs Rasa (5005), Caddy (7860: web page + /webhooks proxy) and, if the
# tunnel credentials are mounted, the "lexi" Cloudflare Tunnel so
# https://lexi.salvadorlomeli.com is served from this container.
FROM python:3.11-slim

ARG CADDY_VERSION=2.8.4
ARG CLOUDFLARED_VERSION=2024.12.2

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" \
    | tar -xz -C /usr/local/bin caddy \
 && curl -fsSL -o /usr/local/bin/cloudflared \
    "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-amd64" \
 && chmod +x /usr/local/bin/cloudflared \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir rasa-pro==3.21.3

# The app folder must be writable: Rasa keeps its SQLite tracker store there.
RUN useradd -m -u 1000 user && mkdir -p /home/user/app && chown user:user /home/user/app
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    LLM_API_HEALTH_CHECK=false PYTHONUNBUFFERED=1
WORKDIR /home/user/app
COPY --chown=user . .
RUN chmod +x start.sh

EXPOSE 7860
CMD ["./start.sh"]
