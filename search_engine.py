"""
ORACLE of Lyngby — Search Engine
=================================
Hybrid retrieval: TF-IDF cosine similarity + field-level boosting over
1700+ real DTU researcher profiles (ORCID + Wikidata + Orbit enriched).

Agentic pipeline: every search records a step-by-step trace of what the
agent did (parse → retrieve → rank → match co-supervisors → explain),
which the UI surfaces inside the results.

Designed to be swapped for embedding-based search (Approach 2) or
extended with a RAG layer (Approach 3) — see the sidebar in the app.
"""

import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from advisors_data import (
    get_available_advisors,
    get_all_advisors,
    build_advisor_document,
)


class OracleSearchEngine:
    """TF-IDF search with field-level boosting over advisor profiles."""

    def __init__(self, available_only: bool = True):
        if available_only:
            self.advisors = get_available_advisors()
        else:
            self.advisors = get_all_advisors()

        # Build composite documents for each advisor
        self.documents = [build_advisor_document(a) for a in self.advisors]

        # Fit TF-IDF on the corpus
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),      # unigrams + bigrams
            max_df=0.9,
            min_df=1,
            sublinear_tf=True,       # log-dampened TF (BM25-like)
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def search(self, query: str, top_k: int = 5) -> dict:
        """
        Return top-k advisors ranked by relevance to the query, plus an
        agentic trace of the pipeline steps performed.

        Returns {"results": [...], "agent_trace": [...]}.
        Each result includes the advisor dict, a relevance score, matched
        terms, and suggested co-supervisors.
        """
        trace = []
        t0 = time.perf_counter()

        # Step 1 — parse query
        n_terms = len(query.split())
        trace.append({
            "step": "Parse query",
            "detail": f"Tokenised the request into {n_terms} terms "
                      f"(unigrams + bigrams, English stop-words removed).",
        })

        # Step 2 — retrieve
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        trace.append({
            "step": "Retrieve",
            "detail": f"Compared the query against {len(self.advisors)} DTU "
                      f"researcher profiles (interests, summaries, "
                      f"publications + abstracts) via TF-IDF cosine similarity.",
        })

        # Step 3 — rank
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.001:
                continue  # skip irrelevant results

            advisor = self.advisors[idx]
            matched = self._explain_match(query, advisor)
            team = self.build_supervision_team(int(idx), k=3)

            results.append({
                "advisor": advisor,
                "score": score,
                "matched_fields": matched,
                "team": team,
            })

        if results:
            trace.append({
                "step": "Rank",
                "detail": f"Ranked candidates by relevance — top match "
                          f"{results[0]['advisor']['name']} at "
                          f"{results[0]['score']:.0%} similarity.",
            })

        # Step 4 — supervision team building
        trace.append({
            "step": "Build supervision teams",
            "detail": "For each recommendation, assembled a supervision team "
                      "from the most similar researcher profiles. DTU rule "
                      "enforced: postdocs, research assistants, and PhD "
                      "students cannot act as main supervisor, so their teams "
                      "always include an assistant/associate/full professor "
                      "(preferably from the same section) as proposed main "
                      "supervisor.",
        })

        elapsed = time.perf_counter() - t0
        trace.append({
            "step": "Done",
            "detail": f"Pipeline completed in {elapsed*1000:.0f} ms. "
                      f"Returning {len(results)} recommendation"
                      f"{'s' if len(results) != 1 else ''}.",
        })

        return {"results": results, "agent_trace": trace}

    def build_supervision_team(self, advisor_idx: int, k: int = 3) -> list:
        """
        Build a supervision team for the advisor at `advisor_idx`, ranking
        all other advisors by profile similarity (shared research concepts,
        publication vocabulary).

        DTU rule: postdocs, research assistants, and PhD students cannot
        be the main supervisor of an MSc thesis. If the matched advisor is
        not supervisor-eligible, the team is guaranteed to include at least
        one assistant/associate/full professor (or other senior staff) —
        preferably from the same section/group — proposed as the main
        supervisor. E.g. if postdoc Ashkan Tashk is the best match, his
        Cognitive Systems colleague Per Bækgaard (Associate Professor)
        joins the team as proposed main supervisor.

        Returns up to k entries: {"advisor", "score", "proposed_role"}.
        """
        advisor = self.advisors[advisor_idx]
        sims = cosine_similarity(
            self.tfidf_matrix[advisor_idx], self.tfidf_matrix
        ).flatten()
        sims[advisor_idx] = -1.0  # exclude self
        order = np.argsort(sims)[::-1]

        team = []
        used = {advisor_idx}

        # Mandatory main supervisor when the match can't supervise alone
        if advisor["role"] != "supervisor":
            main_idx = self._find_main_supervisor(advisor, sims, order)
            if main_idx is not None:
                team.append({
                    "advisor": self.advisors[main_idx],
                    "score": max(float(sims[main_idx]), 0.0),
                    "proposed_role": "main supervisor",
                })
                used.add(main_idx)

        # Fill the remaining slots with the most similar colleagues
        for j in order:
            if len(team) >= k:
                break
            if j in used or sims[j] <= 0.02:
                continue
            candidate = self.advisors[j]
            if candidate["name"] == advisor["name"]:
                continue
            team.append({
                "advisor": candidate,
                "score": float(sims[j]),
                "proposed_role": "co-supervisor",
            })
            used.add(j)
        return team

    def _find_main_supervisor(self, advisor: dict, sims, order):
        """
        Find the best supervisor-eligible colleague for a postdoc/PhD-level
        match: the most similar professor-level researcher from the same
        section if one shares meaningful profile overlap, otherwise the
        most similar supervisor anywhere at DTU.
        """
        best_any = None
        for j in order:
            cand = self.advisors[j]
            if cand["role"] != "supervisor" or cand["name"] == advisor["name"]:
                continue
            # Same section/group with real overlap — ideal main supervisor
            if cand["section"] == advisor["section"] and sims[j] > 0.02:
                return j
            if best_any is None:
                best_any = j
        return best_any

    def _explain_match(self, query: str, advisor: dict) -> dict:
        """Identify which advisor fields contributed to the match."""
        query_terms = {t for t in query.lower().split() if len(t) > 2}
        matched = {}

        # Check research interests / fingerprint concepts
        for interest in advisor["research_interests"]:
            if any(t in interest.lower() for t in query_terms):
                matched.setdefault("research_interests", []).append(interest)

        # Check publication titles
        for pub in advisor["recent_publications"]:
            if any(t in pub.lower() for t in query_terms):
                matched.setdefault("publications", []).append(pub)

        # Check AI-generated research summary
        summary = advisor.get("summary", "")
        if summary and any(t in summary.lower() for t in query_terms):
            matched["summary"] = True

        return matched


def generate_match_explanation(result: dict) -> str:
    """
    Generate a human-readable explanation for why an advisor matched.
    In Approach 3 (RAG), this would be replaced by an LLM call.
    """
    advisor = result["advisor"]
    matched = result["matched_fields"]
    lines = []

    if matched.get("research_interests"):
        lines.append(
            f"**Research alignment:** {', '.join(matched['research_interests'][:6])}"
        )
    if matched.get("publications"):
        lines.append(
            f"**Related publications:** {'; '.join(matched['publications'][:3])}"
        )
    if matched.get("summary") and advisor.get("summary"):
        lines.append(f"**Profile:** {advisor['summary'][:300]}…"
                     if len(advisor["summary"]) > 300
                     else f"**Profile:** {advisor['summary']}")

    if not lines:
        # Fallback: general description
        if advisor.get("pitch"):
            lines.append(f"**Pitch:** {advisor['pitch']}")
        elif advisor["research_interests"]:
            lines.append(
                f"**Research areas:** {', '.join(advisor['research_interests'][:5])}"
            )
        else:
            lines.append(f"**Section:** {advisor['section']}")

    return "\n".join(lines)


# ── RAG-style explanation using Google Gemini API (FREE) ────────────────

def generate_rag_explanation(query: str, results: list, api_key: str = None) -> str:
    """
    Use Google Gemini API to generate natural-language explanations
    for why each advisor matches the student's query.

    Get a FREE API key at: https://aistudio.google.com/apikey
    (no credit card required, generous free tier)
    """
    if not api_key:
        return None

    import requests

    profiles_text = ""
    for i, r in enumerate(results, 1):
        a = r["advisor"]
        team_desc = ", ".join(
            f"{m['advisor']['name']} (proposed {m['proposed_role']})"
            for m in r.get("team", [])
        )
        profiles_text += f"""
--- Advisor {i}: {a['name']} ---
Title: {a['title']}, {a['section']} ({a['department']})
Eligible role: {'main supervisor' if a['role'] == 'supervisor' else 'co-supervisor only (postdoc/research assistant/PhD level — cannot be main supervisor)'}
Research: {', '.join(a['research_interests'][:10]) if a['research_interests'] else 'N/A'}
Summary: {a['summary'][:400] if a['summary'] else 'N/A'}
Recent publications: {'; '.join(a['recent_publications'][:4]) if a['recent_publications'] else 'N/A'}
Suggested supervision team: {team_desc or 'N/A'}
"""

    prompt = f"""You are the ORACLE of Lyngby, a helpful advisor-matching system at DTU.

A Master's student has described their thesis interest:
"{query}"

Here are the top matching advisor profiles:
{profiles_text}

For each advisor, write a concise 2-3 sentence explanation of why they
are a good match for this student's interests. Mention specific
publications or research areas that align. IMPORTANT DTU rule: postdocs,
research assistants, and PhD students cannot be the main supervisor of a
Master's thesis — when the matched advisor is at that level, present the
proposed main supervisor from their suggested supervision team (a
professor-level colleague, e.g. from the same section or project) and
explain how the team works together. Be encouraging but honest.

Format your response as:
### 1. [Advisor Name]
[Explanation]

### 2. [Advisor Name]
[Explanation]

(and so on)
"""

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 1500,
                    "temperature": 0.7,
                },
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass

    return None
