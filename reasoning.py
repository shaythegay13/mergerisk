import json
import logging
import os
import re

from openai import OpenAI

logger = logging.getLogger("aisleguard")

WANDB_BASE = "https://api.inference.wandb.ai/v1"
WANDB_MODEL = os.environ.get("AISLEGUARD_WANDB_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = (
    "You are a warehouse safety analysis agent. Analyze only the supplied observable "
    "video evidence. Do not infer intent, blame, injury, recklessness, or facts not "
    "present in the descriptions. Determine whether the current worker/forklift "
    "interaction appears significant and whether the archive indicates a recurring "
    "pattern.\n\n"
    "Return one JSON object only (no markdown, no prose) with exactly these keys:\n"
    '- "severity": "LOW" | "MEDIUM" | "HIGH"\n'
    '- "observable_reasons": array of short strings grounded in the descriptions\n'
    '- "recurring_pattern": boolean\n'
    '- "pattern_summary": string\n'
    '- "recommendation": string\n'
    '- "should_create_alert": boolean'
)


def _assistant_text(message):
    text = (message.content or "").strip()
    if text:
        return text
    reasoning = getattr(message, "reasoning", None)
    if reasoning:
        return str(reasoning).strip()
    extra = getattr(message, "model_extra", None) or {}
    if extra.get("reasoning"):
        return str(extra["reasoning"]).strip()
    return ""


def _parse_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    for key in (
        "severity",
        "observable_reasons",
        "recurring_pattern",
        "pattern_summary",
        "recommendation",
        "should_create_alert",
    ):
        if key not in parsed:
            raise ValueError(f"missing key {key}")
    if parsed["severity"] not in ("LOW", "MEDIUM", "HIGH"):
        parsed["severity"] = "MEDIUM"
    return parsed


def _fallback(primary, similar, search_summary, base_reasons):
    texts = [primary.get("description", "")] + [
        s.get("description", "") for s in similar
    ]
    moving = sum(
        1
        for t in texts
        if any(
            p in (t or "").lower()
            for p in ("move forward", "approach", "runs toward", "continues to move")
        )
    )
    near = sum(
        1
        for t in texts
        if "forklift" in (t or "").lower() and "person" in (t or "").lower()
    )
    recurring = near >= 3 and moving >= 1
    severity = "HIGH" if (moving >= 1 and near >= 2) else "MEDIUM"
    reasons = base_reasons or ["Worker and forklift both present in warehouse aisle footage"]
    return {
        "severity": severity,
        "observable_reasons": reasons[:6],
        "recurring_pattern": recurring,
        "pattern_summary": (
            "Multiple warehouse clips on sdg_warehouse_cam-2 show workers near forklifts, "
            "including footage where a forklift moves while a worker is in the aisle."
            if recurring
            else "Archive search returned related warehouse proximity footage."
        ),
        "recommendation": (
            "Pause forklift travel when pedestrians occupy the aisle, and review recurring "
            "proximity clips from the VAST archive."
        ),
        "should_create_alert": severity == "HIGH" or recurring,
        "analysis_source": "fallback",
    }


def run_reasoning(primary, similar, search, detections=None):
    api_key = os.environ.get("WANDB_API_KEY")
    # Optional billing/routing scope — must match W&B Playground exactly. A wrong
    # OpenAI-Project value yields 401 invalid_api_key even with a valid API key.
    openai_project = os.environ.get("WANDB_OPENAI_PROJECT", "").strip()
    base_reasons = _observable_reasons(primary.get("description", ""))

    payload = {
        "current_event": {
            "id": primary.get("id"),
            "description": primary.get("description"),
            "object_classes": primary.get("object_classes"),
        },
        "historical_incidents": [
            {"id": s["id"], "description": s.get("description"), "similarity": s.get("similarity")}
            for s in similar
        ],
        "vast_search": {
            "query": search.get("query"),
            "result_count": search.get("result_count"),
            "top_filenames": [
                (r.get("filename"), r.get("similarity_score"))
                for r in (search.get("results") or [])[:5]
            ],
        },
        "yolo_evidence": {
            "proximity_signal": (detections or {}).get("proximity_signal"),
            "co_presence_frames": (detections or {}).get("co_presence_frames"),
            "object_counts": (detections or {}).get("object_counts"),
        },
    }

    if not api_key:
        logger.warning("WANDB_API_KEY missing; using fallback reasoning")
        return _fallback(primary, similar, search, base_reasons)

    try:
        default_headers = (
            {"OpenAI-Project": openai_project} if openai_project else None
        )
        client = OpenAI(
            api_key=api_key,
            base_url=WANDB_BASE,
            default_headers=default_headers,
            timeout=90,
        )
        completion = client.chat.completions.create(
            model=WANDB_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Evidence JSON:\n" + json.dumps(payload, indent=2),
                },
            ],
            temperature=0.1,
            max_tokens=700,
        )
        parsed = _parse_json(_assistant_text(completion.choices[0].message))
        parsed["analysis_source"] = "wandb"
        parsed["model"] = WANDB_MODEL
        parsed = _apply_yolo_guardrails(parsed, detections)
        return parsed
    except Exception as exc:  # noqa: BLE001
        logger.warning("W&B inference failed: %s", exc)
        out = _fallback(primary, similar, search, base_reasons)
        out["model"] = None
        return out


def _apply_yolo_guardrails(parsed, detections):
    if not detections or not detections.get("proximity_signal"):
        return parsed
    reasons = list(parsed.get("observable_reasons") or [])
    note = "YOLO: person and equipment co-detected in the same frame(s)"
    if note not in reasons:
        reasons.insert(0, note)
    parsed["observable_reasons"] = reasons[:8]
    if parsed.get("severity") == "LOW" and (
        parsed.get("recurring_pattern") or detections.get("co_presence_frames", 0) >= 3
    ):
        parsed["severity"] = "MEDIUM"
    if parsed.get("recurring_pattern") and not parsed.get("should_create_alert"):
        parsed["should_create_alert"] = True
    return parsed


def _observable_reasons(description):
    text = (description or "").lower()
    reasons = []
    if any(w in text for w in ("person", "worker", "individual")):
        reasons.append("Worker present in aisle")
    if any(w in text for w in ("forklift", "atlas", "equipment")):
        reasons.append("Forklift / moving equipment present")
    if any(w in text for w in ("aisle", "warehouse", "floor", "grid", "pathway")):
        reasons.append("Shared travel area (warehouse aisle)")
    if any(
        w in text
        for w in ("near", "close", "approach", "move forward", "runs toward", "interaction")
    ):
        reasons.append("Close interaction / limited separation")
    return reasons


def build_alert(reasoning):
    if not (
        reasoning.get("should_create_alert")
        or reasoning.get("severity") == "HIGH"
        or reasoning.get("recurring_pattern")
    ):
        return {"type": "WAREHOUSE_SAFETY_ALERT", "status": "SKIPPED"}
    from datetime import datetime, timezone
    import uuid

    return {
        "id": str(uuid.uuid4()),
        "type": "WAREHOUSE_SAFETY_ALERT",
        "status": "CREATED",
        "severity": reasoning.get("severity", "MEDIUM"),
        "finding": reasoning.get("pattern_summary", ""),
        "recommendation": reasoning.get("recommendation", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
