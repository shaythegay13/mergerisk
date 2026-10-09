"""Summarize VSS YOLO sidecar JSON for proximity demos."""

PROXIMITY_LABELS = frozenset(
    {
        "person",
        "forklift",
        "truck",
        "car",
        "bus",
        "motorcycle",
        "bicycle",
    }
)


def summarize_detections(payload):
    if not payload or not isinstance(payload, dict):
        return {
            "available": False,
            "object_counts": {},
            "co_presence_frames": 0,
            "proximity_signal": False,
            "sample_frames": [],
        }

    counts = dict(payload.get("object_counts") or {})
    frames = payload.get("frames") or []
    co_presence = 0
    samples = []

    for frame in frames:
        labels = {d.get("label") for d in (frame.get("detections") or []) if d.get("label")}
        has_person = "person" in labels
        has_equipment = bool(labels & (PROXIMITY_LABELS - {"person"}))
        if has_person and has_equipment:
            co_presence += 1
            if len(samples) < 3:
                samples.append(
                    {
                        "time_sec": frame.get("time_sec"),
                        "labels": sorted(labels),
                        "detections": frame.get("detections") or [],
                    }
                )

    return {
        "available": True,
        "fps": payload.get("fps"),
        "frame_count": payload.get("frame_count"),
        "detection_count": payload.get("detection_count"),
        "object_counts": counts,
        "object_classes": payload.get("object_classes") or [],
        "co_presence_frames": co_presence,
        "proximity_signal": co_presence >= 1,
        "sample_frames": samples,
        "frames": frames,
    }
