"""
ORACLE of Lyngby — Advisor Database
====================================
Loads real DTU researcher profiles from the enriched JSON datasets
produced by the scraping + enrichment pipeline:

  - advisors_enriched.json      (primary: ORCID + Wikidata + Orbit +
                                 photos + AI summaries/pitches)
  - dtu_supervisors.json        (fallback: same schema, no summaries)
  - dtu_staff_orcids.json       (fallback: base ORCID staff list)

Each researcher is normalised into a flat advisor dict and classified
as a potential main SUPERVISOR or CO-SUPERVISOR based on job title.
"""

import json
import os
import re
from functools import lru_cache

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data sources in order of preference (richest first)
_DATA_SOURCES = [
    "advisors_enriched.json",
    "dtu_supervisors.json",
    "dtu_staff_orcids.json",
]

# ── Role classification from job title ──────────────────────────────────
# Main supervisors: permanent/senior academic staff
_SUPERVISOR_KEYWORDS = (
    "professor", "head of section", "head of division", "head of centre",
    "head of center", "groupleader", "group leader", "senior researcher",
    "senior scientist", "chief consultant",
)
# Excluded from supervision (retired / non-academic)
_INELIGIBLE_KEYWORDS = (
    "emeritus", "emerita", "student assistant", "secretary",
    "administrative", "hr ", "janitor",
)


def classify_role(job_title: str) -> str:
    """
    Classify a researcher as 'supervisor', 'co-supervisor', or 'ineligible'
    based on their job title.
      - Professors, heads of section, group leaders, senior researchers
        → main supervisor
      - Emeritus / administrative staff → ineligible
      - Everyone else (postdocs, researchers, PhDs, engineers)
        → co-supervisor
    """
    title = (job_title or "").lower()
    if any(k in title for k in _INELIGIBLE_KEYWORDS):
        return "ineligible"
    if any(k in title for k in _SUPERVISOR_KEYWORDS):
        return "supervisor"
    return "co-supervisor"


def _normalize(orcid_id: str, raw: dict) -> dict:
    """Map a raw enriched-JSON record onto the flat advisor schema."""
    affiliations = raw.get("affiliations") or []
    department = affiliations[0] if affiliations else "DTU"
    section = affiliations[1] if len(affiliations) > 1 else department

    # Research interests = fingerprint concepts + manual keywords (deduped)
    interests = list(dict.fromkeys(
        (raw.get("fingerprint_concepts") or []) + (raw.get("keywords") or [])
    ))

    publications = raw.get("publications") or []
    pub_titles = [p["title"] for p in publications if p.get("title")]

    # Photo: portraits live in photos/<orcid_id>.jpg. Keep the record's
    # photo field only if the file actually exists locally, otherwise fall
    # back to the ORCID-named file. "photos/default.jpg" is a joke
    # placeholder (Einstein) used for ~1200 records — treat it as "no
    # photo" so the UI shows a question-mark placeholder instead.
    photo = raw.get("photo")
    if photo == "photos/default.jpg":
        photo = None
    if photo and not os.path.exists(os.path.join(_BASE_DIR, photo)):
        photo = None
    if not photo:
        orcid_photo = f"photos/{orcid_id}.jpg"
        if os.path.exists(os.path.join(_BASE_DIR, orcid_photo)):
            photo = orcid_photo

    role = classify_role(raw.get("job_title"))

    # Some Orbit-scraped records use pseudo-ids (e.g. "orbit-jane-doe")
    # instead of a real ORCID — don't build an orcid.org link for those.
    is_real_orcid = bool(re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid_id))

    return {
        "orcid_id": orcid_id,
        "name": raw.get("name") or "Unknown",
        "title": raw.get("job_title") or "Researcher",
        "department": department,
        "section": section,
        "orbit_url": raw.get("orbit_url") or "",
        "orcid_url": f"https://orcid.org/{orcid_id}" if is_real_orcid else None,
        "wikidata_id": raw.get("wikidata_id"),
        "photo": photo,
        "research_interests": interests,
        "recent_publications": pub_titles[:6],
        "publications": publications,
        "summary": raw.get("summary") or "",
        "pitch": raw.get("pitch") or "",
        "role": role,
        "eligible": role != "ineligible",
    }


# Researchers discovered live by the DTU-net exploration agent
# (see dtu_agent.py) are persisted here and merged into the index.
DISCOVERED_FILE = "dtu_discovered.json"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    """Load the richest available dataset, keyed by ORCID id."""
    data = None
    for fname in _DATA_SOURCES:
        path = os.path.join(_BASE_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):  # dtu_supervisors / dtu_staff_orcids
            data = {r["orcid_id"]: r for r in data if r.get("orcid_id")}
        break
    if data is None:
        raise FileNotFoundError(
            f"No advisor dataset found. Expected one of: {_DATA_SOURCES}"
        )

    # Merge researchers discovered live on the DTU net (orbit.dtu.dk)
    disc_path = os.path.join(_BASE_DIR, DISCOVERED_FILE)
    if os.path.exists(disc_path):
        with open(disc_path, encoding="utf-8") as fh:
            discovered = json.load(fh)
        known_names = {
            (r.get("name") or "").lower() for r in data.values()
        }
        for r in discovered:
            rid = r.get("orcid_id")
            if not rid or rid in data:
                continue
            if (r.get("name") or "").lower() in known_names:
                continue
            data[rid] = r
    return data


def reload():
    """Clear caches so newly discovered researchers join the index."""
    _load_raw.cache_clear()
    _load_advisors.cache_clear()


@lru_cache(maxsize=1)
def _load_advisors() -> tuple:
    raw = _load_raw()
    return tuple(_normalize(orcid, rec) for orcid, rec in raw.items())


def get_all_advisors() -> list:
    """Return full advisor list (including ineligible, e.g. emeritus)."""
    return list(_load_advisors())


def get_available_advisors() -> list:
    """Return advisors eligible to supervise or co-supervise."""
    return [a for a in _load_advisors() if a["eligible"]]


def get_supervisors() -> list:
    """Return potential main supervisors (senior academic staff)."""
    return [a for a in _load_advisors() if a["role"] == "supervisor"]


def get_co_supervisors() -> list:
    """Return potential co-supervisors (postdocs, researchers, etc.)."""
    return [a for a in _load_advisors() if a["role"] == "co-supervisor"]


def get_sections() -> list:
    """Return unique sections."""
    return sorted(set(a["section"] for a in _load_advisors()))


def build_advisor_document(advisor: dict) -> str:
    """
    Flatten an advisor profile into a single searchable text document.
    This is the unit we index for retrieval.
    """
    parts = [
        f"{advisor['name']} — {advisor['title']}, {advisor['section']}, {advisor['department']}",
    ]
    if advisor["research_interests"]:
        parts.append(f"Research interests: {', '.join(advisor['research_interests'])}")
    if advisor["summary"]:
        parts.append(advisor["summary"])
    pubs = advisor["publications"]
    if pubs:
        titles = [p["title"] for p in pubs[:10] if p.get("title")]
        parts.append(f"Publications: {'; '.join(titles)}")
        # Include a few truncated abstracts for richer matching
        abstracts = [
            p["abstract"][:500] for p in pubs[:5] if p.get("abstract")
        ]
        if abstracts:
            parts.append(" ".join(abstracts))
    return "\n".join(parts)
