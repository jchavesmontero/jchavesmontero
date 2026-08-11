#!/usr/bin/env python3
"""Refresh the public ADS profile snapshot used by the static website."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request


SEARCH_URL = "https://api.adsabs.harvard.edu/v1/search/query"
METRICS_URL = "https://api.adsabs.harvard.edu/v1/metrics"
PROFILE_URL = (
    "https://ui.adsabs.harvard.edu/search/"
    "fq=%7B!type%3Daqp%20v%3D%24fq_database%7D&"
    "fq_database=(database%3Aastronomy%20OR%20database%3Aphysics)&"
    "q=%20author%3A%22chaves-montero%2C%20j.%22&"
    "sort=date%20desc%2C%20bibcode%20desc/metrics"
)
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "ads-profile.json"


def api_json(url: str, token: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "jchavesmontero-site/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"ADS API returned HTTP {exc.code}: {detail[:500]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach the ADS API: {exc.reason}") from exc


def metric(data: dict, group: str, name: str) -> int:
    try:
        return int(round(float(data[group][name])))
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"ADS response is missing {group!r} / {name!r}") from exc


def main() -> int:
    token = os.environ.get("ADS_API_TOKEN", "").strip()
    if not token:
        print("ADS_API_TOKEN is required", file=sys.stderr)
        return 2

    params = parse.urlencode(
        {
            "q": 'author:"chaves-montero, j."',
            "fq": "database:astronomy OR database:physics",
            "fl": "bibcode",
            "rows": 2000,
            "sort": "date desc,bibcode desc",
        }
    )
    search = api_json(f"{SEARCH_URL}?{params}", token)
    bibcodes = [doc["bibcode"] for doc in search.get("response", {}).get("docs", []) if doc.get("bibcode")]
    if not bibcodes:
        raise RuntimeError("ADS search returned no records; keeping the existing snapshot")

    metrics = api_json(
        METRICS_URL,
        token,
        {"bibcodes": bibcodes, "types": ["basic", "citations", "indicators"]},
    )
    snapshot = {
        "publication_count": metric(metrics, "basic stats", "number of papers"),
        "citation_count": metric(metrics, "citation stats", "total number of citations"),
        "h_index": metric(metrics, "indicators", "h"),
        "updated": datetime.now(timezone.utc).date().isoformat(),
        "estimated": False,
        "source": "NASA/ADS",
        "profile_url": PROFILE_URL,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(OUTPUT)
    print(
        f"Updated ADS profile: {snapshot['publication_count']} papers, "
        f"{snapshot['citation_count']} citations, h={snapshot['h_index']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
