# 🏛️ The ORACLE of Lyngby

**Open Retrieval of Advisors by Course and Literature Expertise**

> A search engine that connects Master's students at DTU with the right thesis advisor.
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

---

## What It Does

A student types in a description of their thesis idea or research interests. ORACLE searches across advisor profiles, publications, course catalogues, and past thesis supervisions, then returns a ranked list with explanations of why each advisor is a good match.

## Architecture

```
Student query
     │
     ▼
┌─────────────────┐
│  TF-IDF Index   │  ← Approach 1: keyword + bigram matching
│  (scikit-learn)  │     with sublinear TF weighting
└────────┬────────┘
         │ top-k results
         ▼
┌─────────────────┐
│  Match Explainer │  ← Approach 2: field-level matching
│  (template)      │     highlights research, courses, pubs
└────────┬────────┘
         │ (optional)
         ▼
┌─────────────────┐
│  RAG Layer       │  ← Approach 3: Anthropic API generates
│  (Claude API)    │     natural-language explanations
└────────┬────────┘
         │
         ▼
   Streamlit UI
```

## Data Sources

The advisor database is populated from:

| Source | What It Provides |
|--------|-----------------|
| `people.compute.dtu.dk` | Names, titles, sections, research interests |
| DTU Orbit (`orbit.dtu.dk`) | Publications, abstracts, co-author networks |
| Kursusbasen (`kurser.dtu.dk`) | Course titles, descriptions, learning objectives |
| Supervised thesis records | Past thesis topics and student projects |

Currently covers **19 advisors** across 8 DTU Compute sections.

## Features

- **Semantic search** with TF-IDF + cosine similarity over composite advisor documents
- **Field-level match explanations** showing which research areas, courses, and publications matched
- **Advisor availability tracking** — warns when advisors are at capacity
- **RAG-powered explanations** (optional, needs Anthropic API key) for rich, contextual recommendations
- **10 example queries** spanning all research areas
- **Responsive UI** with DTU-branded styling

## Extending the System

### Add embedding-based search (Approach 2)
```python
# In search_engine.py, swap TF-IDF for:
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(documents)
```

### Add more advisors
Edit `advisors_data.py` or write a scraper targeting `people.compute.dtu.dk`.

### Build a knowledge graph (Approach 4)
Use co-author data from Orbit + course co-teaching to build an advisor graph.

---

## Project Structure

```
oracle_of_lyngby/
├── app.py              # Streamlit frontend
├── search_engine.py    # TF-IDF search + RAG integration
├── advisors_data.py    # Advisor database + document builder
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Success Level Achieved

| Level | Status |
|-------|--------|
| **Minimum Viable** | ✅ Ranked list from text query with at least one data source |
| **Solid** | ✅ Multiple data sources, explanations, handles both descriptions and keywords |
| **Impressive** | ✅ Contextual recommendations with links, graceful vague queries, polished UI |
| **Above and Beyond** | 🔲 Add advisor clustering, confidence scores, conversational interaction |

---

*Occasionally Reliable Academic Compass for Lost Examinees*
"# Oracle_of_Lyngby" 
