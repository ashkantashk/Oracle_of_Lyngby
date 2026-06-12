"""
ORACLE of Lyngby — DTU-net Exploration Agent
=============================================
Agentic extension: when enabled, the Oracle goes beyond its local index
and live-explores the DTU research net for additional researchers
matching the student's query.

Discovery source: the ORCID public API (pub.orcid.org), filtered to
researchers affiliated with the Technical University of Denmark.
(The DTU Orbit portal itself blocks scripted requests with HTTP 403,
but ORCID iDs are the same keys the local datasets — and the photos/
folder — are indexed by, so discoveries integrate seamlessly.)

Newly discovered researchers can be persisted to dtu_discovered.json,
where advisors_data.py merges them into the search index on reload, so
the list of potential supervisors keeps growing with every exploration.
"""

import json
import os

import requests

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DISCOVERED_PATH = os.path.join(_BASE_DIR, "dtu_discovered.json")

ORCID_SEARCH_URL = "https://pub.orcid.org/v3.0/expanded-search/"
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "OracleOfLyngby/1.0 (DTU Compute hackathon; advisor search)",
}


def explore_dtu_net(query: str, max_results: int = 10, timeout: int = 15):
    """
    Live-search the ORCID public registry for DTU-affiliated researchers
    matching the query. Returns (researchers, status) where researchers
    is a list of {"name", "orcid_id", "orcid_url"} stubs and status is a
    human-readable summary for the agentic trace.
    """
    q = f'affiliation-org-name:"Technical University of Denmark" AND ({query})'
    try:
        resp = requests.get(
            ORCID_SEARCH_URL,
            params={"q": q, "rows": max_results},
            headers=_HEADERS,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return [], (f"Could not reach the DTU net "
                    f"({exc.__class__.__name__}) — showing local index only.")

    found = []
    for item in data.get("expanded-result") or []:
        orcid_id = item.get("orcid-id")
        name = " ".join(
            p for p in (item.get("given-names"), item.get("family-names")) if p
        ).strip()
        if not orcid_id or not name:
            continue
        found.append({
            "name": name,
            "orcid_id": orcid_id,
            "orcid_url": f"https://orcid.org/{orcid_id}",
        })

    total = data.get("num-found", len(found))
    return found, (
        f"Live-queried the ORCID registry for DTU researchers matching "
        f"'{query[:60]}' — {total} on the DTU net, showing top {len(found)}."
    )


def save_discovered(researchers: list, query: str = "") -> int:
    """
    Persist newly discovered researchers to dtu_discovered.json in the
    same raw-record schema the main datasets use, so advisors_data.py
    can merge them into the index. Returns the number actually added.
    """
    existing = []
    if os.path.exists(DISCOVERED_PATH):
        with open(DISCOVERED_PATH, encoding="utf-8") as fh:
            existing = json.load(fh)
    known_ids = {r.get("orcid_id") for r in existing}

    added = 0
    for r in researchers:
        if r["orcid_id"] in known_ids:
            continue
        existing.append({
            "orcid_id": r["orcid_id"],
            "name": r["name"],
            "job_title": None,
            "affiliations": [
                "Technical University of Denmark",
                "Discovered via DTU-net exploration",
            ],
            "keywords": [query] if query else [],
            "fingerprint_concepts": [],
            "orbit_url": "",
            "publications": [],
        })
        known_ids.add(r["orcid_id"])
        added += 1

    if added:
        with open(DISCOVERED_PATH, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, ensure_ascii=False, indent=2)
    return added
