"""
ORACLE of Lyngby — Search Engine
=================================
Hybrid retrieval: TF-IDF cosine similarity + field-level boosting.
Designed to be swapped for embedding-based search (Approach 2) or
extended with a RAG layer (Approach 3) during the hackathon.
"""

import hashlib
from pathlib import Path

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


class ExploreEngine:
    """
    Powers the interactive explore mode.

    Each advisor is represented by a single ``supervisor_summary`` embedding.
    Pairwise preference elicitation asks users to choose between two advisor
    summaries; since there is exactly one embedding per advisor there is no
    need to average across topics.

    Strategy
    --------
    - Cold start (round 0): maximally dissimilar pair of advisors.
    - Adaptive (round ≥ 1): active-learning pair selection at the decision
      boundary. Each advisor gets a contrastive score:
          score(i) = sim(i, p+) − β·sim(i, p−)
      where p+ = normalised mean of chosen embeddings and p− = normalised
      mean of rejected embeddings. Pairs are ranked by:
          uncertainty × diversity = (1 − |score_i − score_j|) × (1 − sim(i,j))
    - Ranking: score is read directly per advisor — no averaging required.
    """

    _CACHE_DIR = Path(__file__).parent / ".cache"

    def __init__(
        self,
        available_only: bool = True,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        try:
            from advisors_data_enriched import get_available_advisors as _get_avail
            from advisors_data_enriched import get_all_advisors as _get_all
        except ImportError:
            _get_avail = get_available_advisors
            _get_all = get_all_advisors

        self.advisors = _get_avail() if available_only else _get_all()

        # One entry per advisor — index equals advisor_idx
        self.topics: list[dict] = [
            {
                "text": advisor.get("supervisor_summary", ""),
                "topic_idx": adv_idx,
                "advisor_idx": adv_idx,
                "advisor_name": advisor["name"],
            }
            for adv_idx, advisor in enumerate(self.advisors)
        ]

        self.embeddings = self._load_embeddings(model_name)

    def _load_embeddings(self, model_name: str) -> np.ndarray:
        """
        Return embeddings for all advisor summaries.
        On a cache hit (texts unchanged) the SentenceTransformer model is never
        loaded — making subsequent starts essentially instant.
        Cache is stored in .cache/ next to search_engine.py, keyed by an MD5
        hash of the concatenated summary texts.
        """
        texts = [t["text"] for t in self.topics]
        texts_hash = hashlib.md5("\n".join(texts).encode()).hexdigest()

        self._CACHE_DIR.mkdir(exist_ok=True)
        emb_file = self._CACHE_DIR / f"explore_embeddings_{texts_hash}.npy"

        if emb_file.exists():
            return np.load(str(emb_file))

        # Cache miss — encode and save
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        np.save(str(emb_file), embeddings)

        # Remove stale cache files for this engine to avoid unbounded growth
        for old in self._CACHE_DIR.glob("explore_embeddings_*.npy"):
            if old != emb_file:
                old.unlink(missing_ok=True)

        return embeddings

    def cold_start_pair(self) -> tuple[int, int]:
        """Return indices of the two most dissimilar advisors."""
        sim = cosine_similarity(self.embeddings, self.embeddings).copy()
        np.fill_diagonal(sim, np.inf)
        flat_idx = int(np.argmin(sim))
        i, j = divmod(flat_idx, len(self.topics))
        return i, j

    def next_advisor(
        self, choices: list[dict], rejections: list[dict], shown_idxs: list[int]
    ) -> int:
        """
        Select the single most informative advisor to show next.

        Cold start (no feedback yet): pick the most central advisor —
        the one with the highest mean similarity to all others, giving
        a representative starting point.

        With feedback: pick the not-yet-shown advisor whose contrastive
        score is closest to zero (maximum uncertainty about preference).
        If all advisors have been shown already, restart from the most
        uncertain across the full set.
        """
        shown_set = set(shown_idxs)
        candidates = [i for i in range(len(self.topics)) if i not in shown_set]

        if not candidates:
            candidates = list(range(len(self.topics)))  # all shown — wrap around

        if not choices and not rejections:
            # Cold start: most representative (central) advisor
            sim_matrix = cosine_similarity(self.embeddings, self.embeddings)
            mean_sim = sim_matrix.sum(axis=1)
            return int(max(candidates, key=lambda i: mean_sim[i]))

        scores = self._contrastive_scores(choices, rejections)
        # Most uncertain = score closest to 0
        return int(min(candidates, key=lambda i: abs(float(scores[i]))))

    def _contrastive_scores(self, choices: list[dict], rejections: list[dict], beta: float = 0.5) -> np.ndarray:
        """
        Per-advisor contrastive score: sim(i, p+) − beta * sim(i, p−)

        p+ = L2-normalised mean of chosen advisor embeddings.
        p− = L2-normalised mean of rejected advisor embeddings (zero if none).
        Returns an (n_advisors,) array; higher = more preferred.
        """
        pos_idxs = [c["topic_idx"] for c in choices]
        p_plus = self.embeddings[pos_idxs].mean(axis=0)
        norm = np.linalg.norm(p_plus)
        p_plus = p_plus / norm if norm > 1e-9 else p_plus
        sim_pos = cosine_similarity(self.embeddings, p_plus.reshape(1, -1)).flatten()

        if rejections:
            neg_idxs = [r["topic_idx"] for r in rejections]
            p_minus = self.embeddings[neg_idxs].mean(axis=0)
            norm = np.linalg.norm(p_minus)
            p_minus = p_minus / norm if norm > 1e-9 else p_minus
            sim_neg = cosine_similarity(self.embeddings, p_minus.reshape(1, -1)).flatten()
        else:
            sim_neg = np.zeros(len(self.topics))

        return sim_pos - beta * sim_neg

    def adaptive_pair(
        self, choices: list[dict], rejections: list[dict], shown_pairs: list
    ) -> tuple[int, int]:
        """
        Select the next pair (i, j) using active learning at the decision boundary.

        Each advisor gets a contrastive score (see _contrastive_scores). The pair
        maximising uncertainty × diversity is chosen:
            (1 − |score_i − score_j|) × (1 − sim(i, j))

        All pairs are cross-advisor by construction (one entry per advisor).
        Already-shown pairs are skipped.
        """
        scores = self._contrastive_scores(choices, rejections)
        sim_matrix = cosine_similarity(self.embeddings, self.embeddings)

        shown_set = {frozenset(p) for p in shown_pairs}
        n = len(self.topics)
        best_pair_score = -np.inf
        best_i, best_j = self.cold_start_pair()  # safe fallback

        for i in range(n):
            for j in range(i + 1, n):
                if frozenset((i, j)) in shown_set:
                    continue
                uncertainty = 1.0 - abs(float(scores[i]) - float(scores[j]))
                diversity = 1.0 - float(sim_matrix[i, j])
                pair_score = uncertainty * diversity
                if pair_score > best_pair_score:
                    best_pair_score = pair_score
                    best_i, best_j = i, j

        return best_i, best_j

    def rank_advisors(
        self, choices: list[dict], rejections: list[dict], top_k: int = 5
    ) -> list[dict]:
        """
        Rank advisors by their contrastive score (one score per advisor).

        Scores are min-max normalised to [0, 1] for display.
        Returns the same result-dict format as OracleSearchEngine.search().
        """
        scores = self._contrastive_scores(choices, rejections)
        top_indices = np.argsort(scores)[::-1][:top_k]

        raw = scores[top_indices]
        lo, hi = raw.min(), raw.max()
        scale = hi - lo if hi > lo else 1.0

        results = []
        for adv_idx in top_indices:
            display_score = (float(scores[adv_idx]) - lo) / scale
            advisor = self.advisors[int(adv_idx)]
            results.append({
                "advisor": advisor,
                "score": display_score,
                "matched_fields": {"supervisor_summary": [advisor.get("supervisor_summary", "")]},
                "score_label": "preference match",
            })

        return results


class EmbeddingSearchEngine:
    """
    Semantic search using sentence-transformer dense embeddings.
    Overcomes the lexical gap of TF-IDF: queries like "neural networks"
    match advisors who write about "deep learning" because the model
    encodes meaning, not just token overlap.
    """

    def __init__(
        self,
        available_only: bool = True,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        from sentence_transformers import SentenceTransformer

        if available_only:
            self.advisors = get_available_advisors()
        else:
            self.advisors = get_all_advisors()

        self.documents = [build_advisor_document(a) for a in self.advisors]

        self.model = SentenceTransformer(model_name)

        # Encode all advisor documents once; L2-normalise so that
        # dot product == cosine similarity at query time.
        self.embeddings = self.model.encode(
            self.documents,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Return top-k advisors ranked by semantic similarity to the query.
        Each result includes the advisor dict + a relevance score + matched terms.
        """
        query_emb = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        scores = cosine_similarity(query_emb, self.embeddings).flatten()

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.1:
                continue  # skip very low-similarity results

            advisor = self.advisors[idx]
            matched = self._explain_match(query, advisor)

            results.append({
                "advisor": advisor,
                "score": score,
                "matched_fields": matched,
            })

        return results

    def _explain_match(self, query: str, advisor: dict) -> dict:
        """Keyword overlap for explainability (same as TF-IDF engine)."""
        query_terms = set(query.lower().split())
        matched = {}

        for interest in advisor["research_interests"]:
            if any(t in interest.lower() for t in query_terms):
                matched.setdefault("research_interests", []).append(interest)

        for course in advisor["courses"]:
            if any(t in course.lower() for t in query_terms):
                matched.setdefault("courses", []).append(course)

        for pub in advisor["recent_publications"]:
            if any(t in pub.lower() for t in query_terms):
                matched.setdefault("publications", []).append(pub)

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


# ── RAG-style explanation using Anthropic API ──────────────────────────

def generate_rag_explanation(query: str, results: list[dict], api_key: str = None) -> str:
    """
    Use the Anthropic API to generate natural-language explanations
    for why each advisor matches the student's query.
    Falls back to template-based explanations if no API key is set.
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
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["content"][0]["text"]
    except Exception:
        pass

    return None
