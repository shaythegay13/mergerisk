import glob
import json
import os
import time

import requests

from clips import SEARCH_QUERY, SEARCH_SETTINGS

REQUEST_TIMEOUT = 60


def ensure_vss_env():
    if os.environ.get("VSS_URL") and os.environ.get("VSS_USERNAME"):
        return
    configs = sorted(glob.glob("/config/*.config"))
    if len(configs) != 1:
        raise RuntimeError("expected exactly one /config/*.config")
    values = {}
    with open(configs[0], encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key] = val
    os.environ.setdefault("VSS_URL", values.get("INGRESS_URL", ""))
    os.environ.setdefault("VSS_USERNAME", values.get("USERNAME", ""))
    os.environ.setdefault("VSS_PASSWORD", values.get("PASSWORD", ""))


class VssClient:
    def __init__(self):
        ensure_vss_env()
        self.base = os.environ["VSS_URL"].rstrip("/")
        self.username = os.environ["VSS_USERNAME"]
        self.password = os.environ["VSS_PASSWORD"]
        self._token = None
        self._token_at = 0.0

    def vss_login(self, force=False):
        if (
            not force
            and self._token
            and (time.time() - self._token_at) < 3500
        ):
            return self._token
        resp = requests.post(
            f"{self.base}/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        self._token_at = time.time()
        return self._token

    def _auth_headers(self, retry=True):
        token = self.vss_login()
        headers = {"Authorization": f"Bearer {token}"}
        return headers, retry

    def _request(self, method, path, **kwargs):
        headers, retry = self._auth_headers()
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        kwargs["headers"] = {**headers, **kwargs.get("headers", {})}
        url = f"{self.base}{path}"
        resp = requests.request(method, url, **kwargs)
        if resp.status_code == 401 and retry:
            self.vss_login(force=True)
            headers, _ = self._auth_headers(retry=False)
            kwargs["headers"] = {**headers, **kwargs.get("headers", {})}
            resp = requests.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def get_segment_metadata(self, source):
        resp = self._request(
            "GET",
            "/api/v1/videos/metadata",
            params={"source": source},
        )
        return resp.json()

    def search_similar_events(self, query=None):
        query = query or SEARCH_QUERY
        body = {
            "query": query,
            **SEARCH_SETTINGS,
        }
        try:
            resp = self._request("POST", "/api/v1/search", json=body)
            data = resp.json()
            results = data.get("results") or []
            return {
                "query": query,
                "live": True,
                "result_count": len(results),
                "results": results,
            }
        except requests.RequestException as exc:
            return {
                "query": query,
                "live": False,
                "result_count": 0,
                "results": [],
                "error": str(exc),
            }

    def stream_request(self, source, range_header=None):
        token = self.vss_login()
        headers = {}
        if range_header:
            headers["Range"] = range_header
        return requests.get(
            f"{self.base}/api/v1/videos/stream",
            params={"source": source, "token": token},
            headers=headers,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        )


def enrich_clip(vss, clip):
    out = dict(clip)
    try:
        meta = vss.get_segment_metadata(clip["source"])
        if meta.get("reasoning_content"):
            out["description"] = meta["reasoning_content"]
        for key in (
            "filename",
            "original_video",
            "segment_start_sec",
            "segment_end_sec",
            "camera_id",
            "location",
            "object_classes",
            "object_counts",
        ):
            if meta.get(key) is not None:
                out[key] = meta[key]
    except requests.RequestException:
        pass
    return out


def merge_historical_with_search(historical, search_results):
    scores = {
        h.get("source"): h.get("similarity_score")
        for h in search_results
        if h.get("source")
    }
    similar = []
    for clip in historical:
        item = {
            "id": clip["id"],
            "source": clip["source"],
            "description": clip.get("description", ""),
            "similarity": scores.get(clip["source"]),
            "from_search": clip["source"] in scores,
            "verified_curated": True,
        }
        if clip.get("filename"):
            item["filename"] = clip["filename"]
        similar.append(item)
    return similar
