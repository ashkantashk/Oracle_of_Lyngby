# 🏛️ The ORACLE of Lyngby

**Open Retrieval of Advisors by Course and Literature Expertise**

> A search engine that connects Master's students at DTU with the right thesis supervisor **and co-supervisor**.
> Built at the DTU Compute Retreat 2026 — *"Have Anarchic Fun with Agentic Coding"*

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

---

## What It Does

A student types in a description of their thesis idea or research interests. ORACLE searches **1,615 eligible DTU researchers** (1,063 potential main supervisors, 552 potential co-supervisors), then returns a ranked list with:

- **Photos** of each recommended supervisor
- A **🎓 Main supervisor / 🤝 Co-supervisor** role badge (derived from job title)
- A **suggested supervision team** for every recommendation, matched by profile similarity. **DTU rule enforced:** postdocs, research assistants, and PhD students cannot be the main supervisor of an MSc thesis — when the best match is at that level, the team always includes an assistant/associate/full professor (preferably from the same section/group) as proposed main supervisor. E.g. if postdoc Ashkan Tashk is the top match, Per Bækgaard (Associate Professor, Cognitive Systems — same group/project) is proposed as main supervisor, with Aqdus Ilyas (postdoc on the same project) as co-supervisor.
- A **🤖 agentic pipeline trace** showing each reasoning step the Oracle performed (parse → retrieve → rank → match co-supervisors → explore DTU net)
- **🌐 Live DTU-net exploration** — an agent that queries the ORCID public registry for DTU-affiliated researchers matching your query and can add new discoveries to the supervisor list (`dtu_discovered.json`) with one click
- Field-level explanations of why each advisor matched

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
│ 2. Retrieve       │  ← TF-IDF index over 1,615 researcher profiles
│   (scikit-learn)  │     (interests, AI summaries, publications + abstracts)
└────────┬─────────┘
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
│ 5. RAG Layer      │  ← Google Gemini API generates natural-language
│   (Gemini free)   │     explanations for the supervision team
└────────┬─────────┘
         ▼
   Streamlit UI  (every step shown in the 🤖 pipeline trace)
```

## Data Sources

The advisor database is built by a scrape-and-enrich pipeline:

| File | What It Provides |
|------|-----------------|
| `dtu_staff_orcids.json` | Base list: 1,704 DTU staff with ORCID iDs, job titles, affiliations, fingerprint concepts (from DTU Orbit) |
| `dtu_supervisors.json` | + Wikidata IDs, publications with abstracts, photo references |
| `advisors_enriched.json` | **Primary source**: + AI-generated research summaries and supervision pitches (1,707 researchers) |
| `photos/` | ~530 researcher portraits keyed by ORCID iD |

`advisors_data.py` loads the richest available file, normalises each record, and classifies researchers as **supervisor** (professors, heads of section, group leaders, senior researchers), **co-supervisor** (postdocs, researchers, engineers), or **ineligible** (emeritus/administrative).

## Features

- **Search across all of DTU** — 1,615 eligible researchers from every department, not just DTU Compute
- **Supervisor + co-supervisor team building** — each result suggests complementary co-supervisors with photos and profile-overlap scores
- **Researcher photos** in result cards (initials placeholder when no portrait is available)
- **Agentic pipeline trace** rendered inside the search results — see exactly how the Oracle reasoned
- **Field-level match explanations** showing which research concepts and publications matched
- **RAG-powered explanations** (optional, free Google Gemini API key) covering the whole supervision team
- **🧬 "Extend the Oracle" sidebar guide** — step-by-step procedure for upgrading to embedding-based search by scraping more supervisors
- **Responsive UI** with DTU-branded styling, light/dark theme support

## Extending the System

The full procedure is documented in-app (sidebar → **🧬 Extend the Oracle**):

### 1. Scrape more supervisors
Crawl `orbit.dtu.dk` (or `people.compute.dtu.dk`) for staff pages and collect names + ORCID iDs into `dtu_staff_orcids.json`.

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
├── search_engine.py          # TF-IDF search + co-supervisor matching + RAG
├── dtu_agent.py              # DTU-net exploration agent (ORCID registry)
├── advisors_data.py          # JSON loader, role classifier, document builder
├── advisors_enriched.json    # Primary dataset (1,707 researchers, enriched)
├── dtu_supervisors.json      # Intermediate dataset (Wikidata + publications)
├── dtu_staff_orcids.json     # Base ORCID staff list
├── photos/                   # Researcher portraits (ORCID-keyed)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Success Level Achieved

| Level | Status |
|-------|--------|
| **Minimum Viable** | ✅ Ranked list from text query with at least one data source |
| **Solid** | ✅ Multiple data sources, explanations, handles both descriptions and keywords |
| **Impressive** | ✅ Contextual recommendations with links, graceful vague queries, polished UI |
| **Above and Beyond** | ✅ 1,615 real researchers, photos, supervisor + co-supervisor team matching, agentic pipeline trace |

---

*Occasionally Reliable Academic Compass for Lost Examinees*

## Demo

![Oracle of Lyngby Demo](photos/demo.gif)
