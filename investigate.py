import urllib.parse

from clips import SEARCH_QUERY, historical_clips, primary_clip
from reasoning import _observable_reasons, build_alert, run_reasoning
from vss import enrich_clip, merge_historical_with_search


def video_url(source):
    return f"/api/video?{urllib.parse.urlencode({'source': source})}"


def run_investigation(vss, primary_id=None):
    steps = [
        {"id": "event_understood", "status": "pending"},
        {"id": "archive_searched", "status": "pending"},
        {"id": "similar_incidents_retrieved", "status": "pending"},
        {"id": "pattern_evaluated", "status": "pending"},
        {"id": "alert_created", "status": "pending"},
    ]

    primary_cfg = primary_clip(primary_id)
    primary = enrich_clip(vss, primary_cfg)
    steps[0]["status"] = "complete"

    search = vss.search_similar_events(SEARCH_QUERY)
    steps[1]["status"] = "complete"

    hist_cfg = [enrich_clip(vss, c) for c in historical_clips()]
    similar = merge_historical_with_search(hist_cfg, search.get("results") or [])
    for item in similar:
        item["video_url"] = video_url(item["source"])
    steps[2]["status"] = "complete"

    reasoning = run_reasoning(primary, similar, search)
    steps[3]["status"] = "complete"

    action = build_alert(reasoning)
    steps[4]["status"] = "complete" if action.get("status") == "CREATED" else "skipped"

    reasons = reasoning.get("observable_reasons") or _observable_reasons(
        primary.get("description", "")
    )

    return {
        "incident": {
            "id": primary.get("id"),
            "source": primary.get("source"),
            "video_url": video_url(primary["source"]),
            "description": primary.get("description", ""),
            "severity": reasoning.get("severity", "MEDIUM"),
            "observable_reasons": reasons,
        },
        "investigation_steps": steps,
        "search": {
            "query": search.get("query", SEARCH_QUERY),
            "result_count": search.get("result_count", 0),
            "live": search.get("live", False),
        },
        "similar_incidents": similar,
        "analysis": {
            "severity": reasoning.get("severity"),
            "recurring_pattern": reasoning.get("recurring_pattern", False),
            "pattern_summary": reasoning.get("pattern_summary", ""),
            "recommendation": reasoning.get("recommendation", ""),
            "analysis_source": reasoning.get("analysis_source", "fallback"),
        },
        "action": action,
    }
