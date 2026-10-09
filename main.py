import logging
import os
import urllib.parse
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from clips import CURATED_CLIPS
from investigate import run_investigation, video_url
from vss import VssClient, enrich_clip, ensure_vss_env

logging.basicConfig(level=logging.INFO)
APP_DIR = Path(__file__).resolve().parent
INDEX_HTML = APP_DIR / "index.html"

ensure_vss_env()
vss = VssClient()
app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/config")
def api_config_legacy():
    """Legacy helper for older UI builds."""
    primary = enrich_clip(vss, next(c for c in CURATED_CLIPS if c["role"] == "primary"))
    return jsonify(
        {
            "primary": {
                **primary,
                "playback_path": video_url(primary["source"]).lstrip("/"),
                "video_url": video_url(primary["source"]),
            }
        }
    )


@app.get("/")
def index():
    if INDEX_HTML.is_file():
        return send_from_directory(APP_DIR, "index.html")
    return jsonify({"ok": True, "service": "aisleguard"})


@app.get("/api/clips")
def api_clips():
    clips = []
    for clip in CURATED_CLIPS:
        enriched = enrich_clip(vss, clip)
        clips.append(
            {
                "id": enriched["id"],
                "role": enriched["role"],
                "source": enriched["source"],
                "description": enriched.get("description", ""),
                "video_url": video_url(enriched["source"]),
                "segment_start_sec": enriched.get("segment_start_sec"),
                "segment_end_sec": enriched.get("segment_end_sec"),
                "camera_id": enriched.get("camera_id"),
                "location": enriched.get("location"),
            }
        )
    return jsonify({"clips": clips})


@app.post("/api/investigate")
def api_investigate():
    body = request.get_json(silent=True) or {}
    primary_id = body.get("primary_clip_id")
    try:
        return jsonify(run_investigation(vss, primary_id=primary_id))
    except KeyError:
        return jsonify({"error": "unknown primary clip id"}), 400
    except Exception as exc:  # noqa: BLE001
        logging.exception("investigate failed")
        return jsonify({"error": str(exc)}), 500


@app.get("/api/video")
def api_video():
    source = request.args.get("source")
    if not source:
        return jsonify({"error": "source required"}), 400
    range_header = request.headers.get("Range")
    upstream = vss.stream_request(source, range_header=range_header)
    if upstream.status_code not in (200, 206):
        return jsonify({"error": "upstream stream failed"}), upstream.status_code

    headers = {}
    for name in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if upstream.headers.get(name):
            headers[name] = upstream.headers[name]
    headers.setdefault("Accept-Ranges", "bytes")

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        generate(),
        status=upstream.status_code,
        headers=headers,
    )


@app.post("/api/search")
def api_search():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400
    data = vss.search_similar_events(query)
    results = []
    for hit in data.get("results") or []:
        src = hit.get("source")
        results.append(
            {
                "filename": hit.get("filename"),
                "description": (hit.get("reasoning_content") or "")[:300],
                "similarity_score": hit.get("similarity_score"),
                "video_url": video_url(src) if src else None,
            }
        )
    return jsonify(
        {
            "query": query,
            "result_count": data.get("result_count", len(results)),
            "live": data.get("live", True),
            "results": results,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
