"""Curated AisleGuard demo clips (team-2 VAST warehouse archive)."""

SEARCH_QUERY = (
    "worker close to a forklift or moving equipment in a warehouse aisle"
)

SEARCH_SETTINGS = {
    "top_k": 12,
    "llm_top_n": 3,
    "min_similarity": 0.05,
    "time_filter": "all",
    "metadata_filters": {
        "location": "warehouse3",
        "camera_id": "sdg_warehouse_cam-2",
    },
    "include_public": True,
    "hybrid_text_weight": 1.0,
}

CURATED_CLIPS = [
    {
        "id": "clip-1",
        "role": "primary",
        "source": (
            "s3://team-2-vss-chunks-segments/segments/"
            "20261001_075529_16face5576497e69c190_03a2937960b9e61f1c99_run_7_seed_900334964"
            ".ceiling_04.rgb_chunk_0000_segment_002_of_002.mp4"
        ),
        "description": (
            "A person wearing a light-colored shirt and dark pants walks away from a blue "
            "and black forklift in a warehouse with a yellowish tint. The forklift, positioned "
            "near the wall, remains stationary as the individual moves further into the space."
        ),
    },
    {
        "id": "clip-2",
        "role": "historical",
        "source": (
            "s3://team-2-vss-chunks-segments/segments/"
            "20261001_075554_16face5576497e69c190_03a2937960b9e61f1c99_run_7_seed_900334964"
            ".eye_00.rgb_chunk_0000_segment_001_of_002.mp4"
        ),
        "description": (
            "A person wearing a light-colored shirt and dark pants stands near a blue forklift "
            "in a warehouse. The forklift begins to move forward slowly. The person then turns "
            "and runs toward the forklift, appearing to interact with it as it continues to move."
        ),
    },
    {
        "id": "clip-3",
        "role": "historical",
        "source": (
            "s3://team-2-vss-chunks-segments/segments/"
            "20261001_075712_16face5576497e69c190_03a2937960b9e61f1c99_run_7_seed_900334964"
            ".eye_03.rgb_chunk_0000_segment_002_of_002.mp4"
        ),
        "description": (
            "A person wearing a light-colored shirt and dark pants walks away from a blue and "
            "brown forklift labeled \"ATLAS\" in a warehouse with a yellowish tint. The forklift "
            "is stationary, and the person moves toward the back of the scene, stopping near the wall."
        ),
    },
    {
        "id": "clip-4",
        "role": "historical",
        "source": (
            "s3://team-2-vss-chunks-segments/segments/"
            "20261001_075737_16face5576497e69c190_03a2937960b9e61f1c99_run_7_seed_900334964"
            ".eye_04.rgb_chunk_0000_segment_002_of_002.mp4"
        ),
        "description": (
            "A person wearing a light-colored short-sleeved shirt and dark pants is seen in a "
            "warehouse environment. The individual is positioned near a forklift, which is "
            "stationary. The person appears to be interacting with the forklift, possibly "
            "preparing to operate it or having just completed a task. The warehouse has shelves "
            "stocked with various items, and the floor is marked with lines."
        ),
    },
]

HISTORICAL_SOURCES = {c["source"] for c in CURATED_CLIPS if c["role"] == "historical"}


def primary_clip(clip_id=None):
    if clip_id:
        for c in CURATED_CLIPS:
            if c["id"] == clip_id and c["role"] == "primary":
                return c
        raise KeyError(clip_id)
    for c in CURATED_CLIPS:
        if c["role"] == "primary":
            return c
    raise RuntimeError("no primary clip configured")


def historical_clips():
    return [c for c in CURATED_CLIPS if c["role"] == "historical"]
