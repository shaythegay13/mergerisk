# AisleGuard — Judges Q&A (one page)

Practice these aloud. Point at the live App when you answer.

## Elevator

**What did you build?**  
AisleGuard — a warehouse safety video agent. It finds similar past incidents in the VAST archive, reasons with W&B, and creates a safety alert when worker–equipment proximity looks like a recurring hazard.

**What problem?**  
Safety teams can’t watch every camera. We turn indexed video into: detect proximity → search history → decide if it’s a pattern → act (alert + recommendation).

**90-second demo**  
Status bar → play hero clip → **Run agent investigation** → Cosmos caption + YOLO person boxes → similar incidents → W&B conclusion → alert. Optional: Ask the archive / Search VAST.

## Partners

| Partner | What to say | Where on screen |
|---------|-------------|-----------------|
| **VAST Data** | Live retrieval: JWT, hybrid search, metadata, stream, stats, agent Q&A. No mock video. | Status bar, search hits, similar clips, Ask/Search |
| **NVIDIA Cosmos** | Captions from Cosmos3-Reason at ingest (`reasoning_content`); we don’t author them. | Event description after Investigate |
| **NVIDIA YOLO11** | Ingest detections; we overlay bboxes. **Person** reliable; **forklift** not a YOLO class here. | Badge + boxes on hero video |
| **Weights & Biases** | Serverless inference → severity, pattern, recommendation, create/skip alert. Fallback if down. | Conclusion “Agent reasoning · W&B” |
| **CoreWeave** | We don’t provision it; GPUs for Cosmos/YOLO/Embed/W&B are CoreWeave-backed in this challenge. | Honest claim in footer / reasoning meta |
| **Cursor** | How we built & deployed — not a runtime dependency. | README / briefing |

## Technical

**Why an “agent,” not just search?**  
Multi-step decision loop: understand → search → retrieve similar → evaluate pattern → create or skip alert.

**How deployed?**  
Team K8s: `python:3.12-slim`, ConfigMap code, VSS + W&B secrets, Ingress `/app` → workshop **App** button.

**Are alerts persisted?**  
In-memory session log for the demo. Next: VastDB so alerts survive restarts.

**Why curated clips?**  
Reliable live demo on known warehouse segments; still merge live search scores when those sources appear in results.

## Hard questions (honest)

**No forklift boxes?**  
YOLO sidecars don’t label forklift. Person overlays are real; equipment proximity comes from Cosmos + archive search.

**W&B status red but Investigate worked?**  
Status probes `/v1/models` (can 403); Investigate uses chat completions. Trust the investigation result for the demo.

**Empty search?**  
Check filters / ingest lag — don’t debug live. Curated historical clips still carry the story.

**Privacy / liability?**  
Observable evidence only — no intent or blame. Output is operational guidance, not disciplinary claims.

## Close

**Who’s the user?** Warehouse EHS / security ops who need “is this near-miss a pattern?” in minutes.

**What’s next?** Persist alerts to VastDB, notify on threshold, YOLO overlay before Investigate.

**Why us?** End-to-end on the real builders stack — search → reason → act — with each sponsor visible in one clickable demo.

### One-liners

- **Product:** Video agent that investigates aisle near-misses and raises a safety alert.  
- **VAST:** Live hybrid search + archive — the agent’s memory.  
- **Cosmos:** Natural-language understanding of each clip at ingest.  
- **YOLO:** Person boxes on evidence; equipment via captions + search.  
- **W&B:** Judgment layer — severity, pattern, alert or not.
