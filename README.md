# 🏛️ The ORACLE of Lyngby

**Open Retrieval of Advisors by Course and Literature Expertise**

> A search engine that connects Master's students at DTU with the right thesis supervisor **and co-supervisor** — and that **grows its own supervisor index** by exploring the DTU research net live.
> Built at the DTU Compute Retreat 2026 — *"Have Anarchic Fun with Agentic Coding"*

## Demo

![Oracle of Lyngby Demo](photos/demo.gif)
---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

**Optional — RAG explanations:** store a free Gemini API key (from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)) in
`.streamlit/secrets.toml` (gitignored — never commit API keys):

```toml
GEMINI_API_KEY = "AIza..."
```

The key can also be supplied via the `GEMINI_API_KEY` environment variable or pasted directly into the sidebar.

---

## What It Does

A student types in a description of their thesis idea or research interests. ORACLE searches **1,615+ eligible DTU researchers** (1,063 potential main supervisors, 552+ potential co-supervisors — the index grows with every DTU-net discovery), then returns a ranked list with:

- **Photos** of each recommended supervisor
- A **🎓 Main supervisor / 🤝 Co-supervisor** role badge (derived from job title)
- A **suggested supervision team** for every recommendation, matched by profile similarity. **DTU rule enforced:** postdocs, research assistants, and PhD students cannot be the main supervisor of an MSc thesis — when the best match is at that level, the team always includes an assistant/associate/full professor (preferably from the same section/group) as proposed main supervisor. E.g. if postdoc Ashkan Tashk is the top match, Per Bækgaard (Associate Professor, Cognitive Systems — same group/project) is proposed as main supervisor, with Aqdus Ilyas (postdoc on the same project) as co-supervisor.
- A **🤖 agentic pipeline trace** showing each reasoning step the Oracle performed (parse → retrieve → rank → build supervision teams → explore DTU net)
- **🌐 Live DTU-net exploration** — an agent that queries the ORCID public registry for DTU-affiliated researchers matching your query, flags which ones are 🆕 not yet indexed, and adds them to the supervisor list with one click
- **Self-growing index** — discoveries are persisted to `dtu_discovered.json` and merged into the search index on reload, so the Oracle knows more researchers after every exploration
- **Expandable full profiles** per result — research interests / fingerprint concepts, recent publications, and an AI-generated research summary
- Field-level explanations of why each advisor matched, with links to their Orbit, ORCID, and Wikidata pages

## Architecture (agentic pipeline)

```
Student query
     │
     ▼
┌──────────────────┐
│ 1. Parse          │  ← tokenise query (unigrams + bigrams)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. Retrieve       │  ← TF-IDF index (sublinear TF, BM25-like) over
│   (scikit-learn)  │     all researcher profiles (interests, AI
└────────┬─────────┘     summaries, publications + abstracts)
         ▼
┌──────────────────┐
│ 3. Rank           │  ← cosine similarity, top-k results
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. Build          │  ← profile-similarity search assembles a
│   supervision     │     supervision team; postdoc/PhD-level matches
│   teams           │     always get a professor-level main supervisor
└────────┬─────────┘
         ▼ (optional)
┌──────────────────┐
│ 5. Explore        │  ← live ORCID-registry search for DTU researchers
│   DTU net         │     matching the query; new finds can be saved to
└────────┬─────────┘     dtu_discovered.json and join the index
         ▼ (optional)
┌──────────────────┐
│ 6. RAG Layer      │  ← Google Gemini (gemini-2.0-flash, free tier)
│   (Gemini free)   │     generates natural-language explanations
└────────┬─────────┘     for the whole supervision team
         ▼
   Streamlit UI  (every step shown in the 🤖 pipeline trace)
```

## Data Sources

The advisor database is built by a scrape-and-enrich pipeline — and keeps growing at runtime:

| File | What It Provides |
|------|-----------------|
| `dtu_staff_orcids.json` | Base list: 1,704 DTU staff with ORCID iDs, job titles, affiliations, fingerprint concepts (from DTU Orbit) |
| `dtu_supervisors.json` | + Wikidata IDs, publications with abstracts, photo references |
| `advisors_enriched.json` | **Primary source**: + AI-generated research summaries and supervision pitches (1,707 researchers) |
| `dtu_discovered.json` | **Live-grown**: researchers found by the DTU-net exploration agent, merged into the index on reload |
| `photos/` | ~530 researcher portraits keyed by ORCID iD |

`advisors_data.py` loads the richest available file, merges in the live discoveries, normalises each record, and classifies researchers as **supervisor** (professors, heads of section/division/centre, group leaders, senior researchers/scientists, chief consultants), **co-supervisor** (postdocs, researchers, engineers, PhD students), or **ineligible** (emeritus/administrative). Records without a portrait fall back to `photos/<orcid>.jpg` when present; otherwise the UI shows a placeholder.

## Features

- **Search across all of DTU** — 1,615+ eligible researchers from every department, not just DTU Compute
- **🌐 Agentic DTU-net exploration** — live ORCID-registry search per query; one click persists new researchers to `dtu_discovered.json` and rebuilds the index, so the supervisor list grows organically
- **Supervisor + co-supervisor team building** — each result suggests complementary co-supervisors with photos and profile-overlap scores, with the DTU main-supervisor eligibility rule enforced
- **Researcher photos** in result cards (placeholder when no portrait is available)
- **Agentic pipeline trace** rendered inside the search results — see exactly how the Oracle reasoned, with timings
- **Field-level match explanations** showing which research concepts, publications, and summary text matched
- **Full-profile expanders** per result: fingerprint concepts, recent publications, AI research summary, and Orbit / ORCID / Wikidata links
- **RAG-powered explanations** (optional, free Google Gemini API key) covering the whole supervision team and the DTU supervision rules
- **Search settings sidebar** — number of results (1–15), eligible-advisors-only filter, pipeline-trace toggle, DTU-net exploration toggle
- **12 one-click example queries** spanning DTU research areas (eye tracking, medical AI fairness, TinyML, wind energy, quantum photonics, …)
- **🧬 "Extend the Oracle" sidebar guide** — step-by-step procedure for upgrading to embedding-based search by scraping more supervisors
- **Responsive UI** with DTU-branded styling, light/dark theme support, and a scroll-to-top button

## Extending the System

The full procedure is documented in-app (sidebar → **🧬 Extend the Oracle**):

### 1. Scrape more supervisors
Crawl `orbit.dtu.dk` (or `people.compute.dtu.dk`) for staff pages and collect names + ORCID iDs into `dtu_staff_orcids.json` — or simply keep using the in-app **🌐 Explore the DTU net** agent, which discovers researchers via the ORCID public registry (Orbit itself blocks scripted requests) and saves them to `dtu_discovered.json`.

### 2. Enrich each profile
Query the ORCID public API and Wikidata for publications, abstracts, photos, and fingerprint concepts → `dtu_supervisors.json` → `advisors_enriched.json`.

### 3. Add embedding-based search (Approach 2)
```python
# In search_engine.py, swap TF-IDF for:
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(
    [build_advisor_document(a) for a in advisors]
)
# Store in a FAISS index, replace cosine ranking with nearest-neighbour search
```

### 4. Build a knowledge graph (Approach 4)
Use co-author data from Orbit + course co-teaching to build an advisor graph.

---

## Project Structure

```
oracle_of_lyngby/
├── app.py                    # Streamlit frontend (photos, teams, agentic trace)
├── search_engine.py          # TF-IDF search + supervision-team building + RAG
├── dtu_agent.py              # DTU-net exploration agent (ORCID public registry)
├── advisors_data.py          # JSON loader, role classifier, discovery merger
├── advisors_enriched.json    # Primary dataset (1,707 researchers, enriched)
├── dtu_supervisors.json      # Intermediate dataset (Wikidata + publications)
├── dtu_staff_orcids.json     # Base ORCID staff list
├── dtu_discovered.json       # Researchers discovered live on the DTU net
├── photos/                   # Researcher portraits (ORCID-keyed) + demo GIF
├── .streamlit/secrets.toml   # Gitignored — GEMINI_API_KEY lives here
├── config.toml               # Streamlit theme (DTU red accent)
├── requirements.txt          # streamlit, scikit-learn, pandas, numpy, requests
└── README.md                 # This file
```

## Success Level Achieved

| Level | Status |
|-------|--------|
| **Minimum Viable** | ✅ Ranked list from text query with at least one data source |
| **Solid** | ✅ Multiple data sources, explanations, handles both descriptions and keywords |
| **Impressive** | ✅ Contextual recommendations with links, graceful vague queries, polished UI |
| **Above and Beyond** | ✅ 1,615+ real researchers, photos, supervisor + co-supervisor team matching, agentic pipeline trace, live DTU-net exploration with a self-growing index |

---

*Occasionally Reliable Academic Compass for Lost Examinees*
<<<<<<< HEAD

## Demo

![Oracle of Lyngby Demo](photos/demo.gif)
=======
>>>>>>> c57451b0f9539352f2d7213dd038f34b72322087
