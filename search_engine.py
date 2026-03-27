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


class ExploreEngine:
    """
    Powers the interactive explore mode.

    Pre-embeds every supervised_topic across all advisors, then surfaces
    topic pairs for pairwise preference elicitation.

    Strategy
    --------
    - Cold start (round 0): maximally dissimilar cross-advisor pair.
    - Adaptive (round ≥ 1): active-learning pair selection at the decision
      boundary. Each topic gets a contrastive score:
          score(i) = sim(i, p+) − β·sim(i, p−)
      where p+ = normalised mean of chosen embeddings and p− = normalised
      mean of rejected embeddings. Pairs are then ranked by:
          uncertainty × diversity = (1 − |score_i − score_j|) × (1 − sim(i,j))
      High uncertainty means the model cannot yet distinguish which topic the
      user would prefer; high diversity keeps exploration broad.
    - Ranking: each advisor scored by their *mean* contrastive score across
      all their topics (not max), so a single matching topic cannot dominate.
    """

    def __init__(
        self,
        available_only: bool = True,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        from sentence_transformers import SentenceTransformer

        self.advisors = get_available_advisors() if available_only else get_all_advisors()

        # Flatten all topics; store topic_idx for fast embedding lookup
        self.topics: list[dict] = []
        for adv_idx, advisor in enumerate(self.advisors):
            for topic in advisor["supervised_topics"]:
                self.topics.append({
                    "text": topic,
                    "topic_idx": len(self.topics),
                    "advisor_idx": adv_idx,
                    "advisor_name": advisor["name"],
                })

        self.model = SentenceTransformer(model_name)
        self.embeddings = self.model.encode(
            [t["text"] for t in self.topics],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def cold_start_pair(self) -> tuple[int, int]:
        """
        Return indices (i, j) of the two topics that are maximally
        semantically dissimilar and come from different advisors.
        """
        sim = cosine_similarity(self.embeddings, self.embeddings)
        n = len(self.topics)

        # Mask out same-advisor pairs and the diagonal (self-similarity = 1.0)
        for i in range(n):
            for j in range(n):
                if self.topics[i]["advisor_idx"] == self.topics[j]["advisor_idx"]:
                    sim[i, j] = np.inf  # won't be chosen as minimum

        np.fill_diagonal(sim, np.inf)

        flat_idx = int(np.argmin(sim))
        i, j = divmod(flat_idx, n)
        return i, j

    def _contrastive_scores(self, choices: list[dict], rejections: list[dict], beta: float = 0.5) -> np.ndarray:
        """
        Per-topic contrastive score: sim(i, p+) − beta * sim(i, p−)

        p+ = L2-normalised mean of chosen topic embeddings.
        p− = L2-normalised mean of rejected topic embeddings (zero vector if none).
        Returns a (n_topics,) array; higher = more preferred.
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

        Each topic gets a contrastive score (see _contrastive_scores). The pair
        maximising uncertainty × diversity is chosen:
            (1 − |score_i − score_j|) × (1 − sim(i, j))

        Where scores are similar the model is uncertain which the user prefers,
        making it the most informative question. Diversity keeps exploration broad.
        Only cross-advisor, not-yet-shown pairs are considered.
        """
        scores = self._contrastive_scores(choices, rejections)
        sim_matrix = cosine_similarity(self.embeddings, self.embeddings)

        shown_set = {frozenset(p) for p in shown_pairs}
        n = len(self.topics)
        best_pair_score = -np.inf
        best_i, best_j = self.cold_start_pair()  # safe fallback

        for i in range(n):
            for j in range(i + 1, n):
                if self.topics[i]["advisor_idx"] == self.topics[j]["advisor_idx"]:
                    continue
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
        Rank advisors by their *mean* contrastive score across all their topics.

        Using the mean (rather than max) prevents a single highly-matching topic
        from dominating; advisors with broad alignment rank higher than those
        with one very close topic but many unrelated ones.
        Scores are min-max normalised to [0, 1] across the returned top-k for display.
        Returns the same result-dict format as OracleSearchEngine.search().
        """
        scores = self._contrastive_scores(choices, rejections)

        n_advisors = len(self.advisors)
        advisor_topic_data: list[list[tuple]] = [[] for _ in range(n_advisors)]

        for t_idx, topic in enumerate(self.topics):
            adv_idx = topic["advisor_idx"]
            advisor_topic_data[adv_idx].append((float(scores[t_idx]), topic["text"]))

        # Mean contrastive score per advisor
        advisor_mean_scores = np.array([
            np.mean([s for s, _ in ts]) if ts else -np.inf
            for ts in advisor_topic_data
        ])

        top_indices = np.argsort(advisor_mean_scores)[::-1][:top_k]

        # Min-max normalise display scores across the returned set
        raw = advisor_mean_scores[top_indices]
        lo, hi = raw.min(), raw.max()
        scale = hi - lo if hi > lo else 1.0

        results = []
        for adv_idx in top_indices:
            raw_score = float(advisor_mean_scores[adv_idx])
            display_score = (raw_score - lo) / scale
            advisor = self.advisors[int(adv_idx)]
            best_topics = sorted(advisor_topic_data[int(adv_idx)], reverse=True)[:3]
            matched = {"supervised_topics": [t for _, t in best_topics]}
            results.append({
                "advisor": advisor,
                "score": display_score,
                "matched_fields": matched,
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
