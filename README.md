# AisleGuard

Warehouse worker–forklift proximity agent on the VAST Video Search stack. Demo clips are fixed curated segments on `warehouse3` / `sdg_warehouse_cam-2` (team-2 archive).

**Open the app:** [workshop.thecosmoslabs.com](https://workshop.thecosmoslabs.com) → **App** (Ingress path `/app`).

## Demo flow (~2 minutes)

1. Confirm the status bar: VSS connected, indexed clip counts, W&B inference ready.
2. Click **Run agent investigation** — Cosmos captions + YOLO evidence, VAST search, W&B reasoning, alert log.
3. Optional: **Ask the archive** (VAST agent Q&A) or **Search VAST** for hybrid retrieval.

## Built with

- **[Cursor](https://cursor.com)** — AI coding agent / IDE used to build and deploy this application (development environment, not a runtime dependency).

## Partner Technology

### VAST Data

AisleGuard reads the team’s **indexed video archive** through the VSS retrieval API (JWT auth). No mock video data in the investigation path.

| Capability | API | Code |
|------------|-----|------|
| Login | `POST /api/v1/auth/login` | `vss.py` → `VssClient.vss_login` |
| Hybrid / semantic search | `POST /api/v1/search` | `vss.py` → `search_similar_events`; settings in `clips.py` |
| Segment metadata (Cosmos caption, timing, objects) | `GET /api/v1/videos/metadata?source=` | `vss.py` → `get_segment_metadata`, `enrich_clip` |
| Stream hero + similar clips | `GET /api/v1/videos/stream?source=&token=` | `vss.py` → `stream_request`; proxied at `GET /api/video` in `main.py` |
| Archive stats (status bar) | `GET /api/v1/dashboard/stats` | `vss.py` → `dashboard_overview` |
| Agent Q&A | `POST /api/v1/agent/search-and-answer` | `vss.py` → `agent_search_and_answer`; `POST /api/ask-archive` |

**Fields used:** `reasoning_content` (caption), `object_classes`, `segment_*_sec`, `camera_id`, `location`, `filename`, `source`, search `similarity_score`, `results[]`.

**Similar incidents:** Three **historical curated clips** are real indexed segment URIs in `clips.py`. At investigate time, captions are refreshed from VAST metadata; search similarity scores are merged when those sources appear in live search results (`vss.py` → `merge_historical_with_search`).

### NVIDIA Cosmos

Video **descriptions are not authored in AisleGuard**. They are produced at ingest by **NVIDIA Cosmos3-Reason** in the VSS pipeline and stored on each segment row. The app uses the VSS field **`reasoning_content`** from `/videos/metadata` as the event description (`enrich_clip` in `vss.py`). That text flows into the investigation UI, W&B evidence JSON, and optional archive Q&A evidence.

Cosmos Embed1 vectors power hybrid search via the backend; AisleGuard does not call Cosmos GPU endpoints directly.

### NVIDIA YOLO11

Object detection runs at **ingest** (YOLO11 sidecars). AisleGuard only reads **`GET /api/v1/videos/detections?source=`** (`vss.py` → `get_detections`, summarized in `detections.py`). For the demo warehouse clips, sidecars reliably include **person** detections; **forklift** is not a YOLO class in these sidecars—proximity reasoning relies on Cosmos captions + VAST search. The UI draws bbox overlays when detection frames exist.

### Weights & Biases

Investigation reasoning calls **W&B Serverless Inference** (`https://api.inference.wandb.ai/v1/chat/completions`) via the OpenAI-compatible client in `reasoning.py`. Successful runs set **`analysis_source": "wandb"`** on the `/api/investigate` response.

Environment (Kubernetes secret `aisleguard-wandb`): `WANDB_API_KEY` (required), `WANDB_TEAM` / `WANDB_PROJECT` (optional; do **not** send a wrong `OpenAI-Project` header). Default model: `openai/gpt-oss-120b` (`AISLEGUARD_WANDB_MODEL` to override).

If W&B is unreachable, the app falls back to rule-based analysis (`analysis_source": "fallback"`) so the demo still completes.

### CoreWeave

AisleGuard does **not** provision CoreWeave infrastructure. In the Builders Challenge architecture, **Cosmos, YOLO, Embed, and W&B serverless inference run on GPU compute backed by CoreWeave** (see repo `ARCHITECTURE_REFERENCE.md`). Our app consumes those capabilities through VSS and W&B APIs only.

### Cursor

Listed under **Built with** — development agent only.

## Architecture

```
Warehouse Video
      ↓
NVIDIA Cosmos + YOLO
      ↓
VAST Data / VSS Index
      ↓
Semantic Search + Video Retrieval
      ↓
AisleGuard Agent
      ↓
W&B Serverless Inference
      ↓
CoreWeave GPU Compute
      ↓
Safety Alert
```

## Verification checklist (live app)

| Sponsor / partner | Demonstrated in live app? | Where to see it |
|-------------------|---------------------------|-----------------|
| **VAST Data** | Yes | Status bar clip counts; investigate search hit count; similar clip playback; Ask the archive / Search VAST |
| **NVIDIA Cosmos** | Yes | Event captions after investigate; chip “Video understanding · NVIDIA Cosmos”; metadata-driven descriptions |
| **NVIDIA YOLO11** | Partial (person bboxes) | YOLO overlay on primary clip when detections exist; evidence list object counts |
| **Weights & Biases** | Yes (when reachable) | `analysis_source: wandb` in investigate response; “Agent reasoning · Weights & Biases” in conclusion |
| **CoreWeave** | Indirect (accurate claim) | README + UI footnote: GPU inference on CoreWeave-backed endpoints |
| **Cursor** | Dev only | This README “Built with” section |
