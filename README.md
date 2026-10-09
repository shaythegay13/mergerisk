# AisleGuard (MergeRisk)

Warehouse safety video agent for the VAST Builders Challenge: monitors worker–forklift proximity, searches the VAST archive for similar incidents, reasons over evidence with Weights & Biases Serverless Inference, and creates in-memory safety alerts.

## Stack

- **VAST VSS** — Cosmos captions, semantic search, video streaming (server-side proxy)
- **W&B Inference** — structured risk analysis JSON
- **Flask** — API + single-page demo UI

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# VSS_URL, VSS_USERNAME, VSS_PASSWORD from team config; WANDB_* for reasoning
python main.py
```

Open `http://localhost:8080` (or deploy to team Kubernetes at Ingress `/app`).

## API

- `GET /health` — `{"ok": true}`
- `GET /api/clips` — four curated warehouse clips
- `POST /api/investigate` — full demo loop
- `GET /api/video?source=...` — proxied VAST stream (no JWT in browser)
- `POST /api/search` — optional semantic search

## Deploy

Uses the hackathon `deploy-app-no-registry` pattern: ConfigMap + `python:3.12-slim`, `VSS_URL=http://video-backend-service:8000` in-cluster.
