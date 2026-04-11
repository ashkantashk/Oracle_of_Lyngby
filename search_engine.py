"""
ORACLE of Lyngby — Search Engine
=================================
Hybrid retrieval: TF-IDF cosine similarity + field-level boosting.
Designed to be swapped for embedding-based search (Approach 2) or
extended with a RAG layer (Approach 3) during the hackathon.
"""

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

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Return top-k advisors ranked by relevance to the query.
        Each result includes the advisor dict + a relevance score + matched terms.
        """
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k indices sorted by descending score
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.001:
                continue  # skip irrelevant results

            advisor = self.advisors[idx]

            # Find which terms matched
            matched = self._explain_match(query, advisor)

            results.append({
                "advisor": advisor,
                "score": score,
                "matched_fields": matched,
            })

        return results

    def _explain_match(self, query: str, advisor: dict) -> dict:
        """Identify which advisor fields contributed to the match."""
        query_terms = set(query.lower().split())
        matched = {}

        # Check research interests
        for interest in advisor["research_interests"]:
            if any(t in interest.lower() for t in query_terms):
                matched.setdefault("research_interests", []).append(interest)

        # Check courses
        for course in advisor["courses"]:
            if any(t in course.lower() for t in query_terms):
                matched.setdefault("courses", []).append(course)

        # Check publications
        for pub in advisor["recent_publications"]:
            if any(t in pub.lower() for t in query_terms):
                matched.setdefault("publications", []).append(pub)

        # Check supervised topics
        for topic in advisor["supervised_topics"]:
            if any(t in topic.lower() for t in query_terms):
                matched.setdefault("supervised_topics", []).append(topic)

        return matched


def generate_match_explanation(result: dict) -> str:
    """
    Generate a human-readable explanation for why an advisor matched.
    In Approach 3 (RAG), this would be replaced by an LLM call.
    """
    advisor = result["advisor"]
    matched = result["matched_fields"]
    score = result["score"]
    lines = []

    if matched.get("research_interests"):
        lines.append(
            f"**Research alignment:** {', '.join(matched['research_interests'])}"
        )
    if matched.get("courses"):
        lines.append(
            f"**Relevant courses:** {', '.join(matched['courses'])}"
        )
    if matched.get("publications"):
        lines.append(
            f"**Related publications:** {'; '.join(matched['publications'])}"
        )
    if matched.get("supervised_topics"):
        lines.append(
            f"**Past thesis supervision:** {', '.join(matched['supervised_topics'])}"
        )

    if not lines:
        # Fallback: general description
        lines.append(
            f"**Research areas:** {', '.join(advisor['research_interests'][:3])}"
        )

    return "\n".join(lines)


# ── RAG-style explanation using Google Gemini API (FREE) ────────────────

def generate_rag_explanation(query: str, results: list[dict], api_key: str = None) -> str:
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
        profiles_text += f"""
--- Advisor {i}: {a['name']} ---
Title: {a['title']}, {a['section']}
Research: {', '.join(a['research_interests'])}
Courses: {', '.join(a['courses']) if a['courses'] else 'N/A'}
Recent publications: {'; '.join(a['recent_publications'])}
Past thesis topics: {'; '.join(a['supervised_topics'])}
Availability: {a['availability']} ({a['current_students']}/{a['max_students']} students)
"""

    prompt = f"""You are the ORACLE of Lyngby, a helpful advisor-matching system at DTU.

A Master's student has described their thesis interest:
"{query}"

Here are the top matching advisor profiles:
{profiles_text}

For each advisor, write a concise 2-3 sentence explanation of why they
are a good match for this student's interests. Mention specific
publications, courses, or research areas that align. If the advisor has
limited availability, note this. Be encouraging but honest.

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
