"""
╔══════════════════════════════════════════════════════════════╗
║          THE ORACLE OF LYNGBY                               ║
║   Open Retrieval of Advisors by Course and                  ║
║   Literature Expertise                                      ║
║                                                             ║
║   DTU Compute Retreat Hackathon — Agentic Coding            ║
╚══════════════════════════════════════════════════════════════╝

Theme strategy:
  All text/background colors use Streamlit's built-in CSS variables
  (--text-color, --background-color, --secondary-background-color)
  which automatically adapt to light/dark mode.
  Only brand accent colors (DTU red, oracle gold) are hardcoded.

Data: 1700+ real DTU researchers loaded from advisors_enriched.json
  (ORCID + Wikidata + Orbit + photos + AI summaries).
"""

import base64
import os
import re
import time
import html as html_module

import streamlit as st

st.set_page_config(
    page_title="The ORACLE of Lyngby",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — uses Streamlit theme vars for auto dark/light support ─────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Source+Sans+3:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/*
  Streamlit exposes these theme-aware CSS variables:
    --text-color            (adapts to dark/light)
    --background-color      (main bg)
    --secondary-background-color (surface/sidebar bg)
    --primary-color         (accent, set to DTU red via config.toml)
    --font                  (theme font)
  We use these for ALL text and background colors so everything
  automatically adapts when the user toggles dark mode.
*/

:root {
    --dtu-red: #990000;
    --oracle-gold: #c9a84c;
    --radius: 12px;
}

.block-container { padding-top: 2rem !important; max-width: 1100px !important; }

/* ── Fonts only — no color overrides on native elements ──────────── */
h1, h2, h3 { font-family: 'DM Serif Display', serif !important; }
/* IMPORTANT: span is deliberately excluded here.
   Streamlit uses <span> elements with font-family "Material Symbols Rounded"
   for icons like the sidebar collapse arrow. If we override span with
   !important, the icon font gets replaced and icon names render as text. */
p, li, div, label, .stMarkdown { font-family: 'Source Sans 3', sans-serif !important; }
code, .stCode { font-family: 'JetBrains Mono', monospace !important; }

/* ── Hero ────────────────────────────────────────────────────────── */
.hero-container {
    text-align: center; padding: 2rem 0 1.5rem 0;
    border-bottom: 2px solid var(--dtu-red); margin-bottom: 2rem;
}
.hero-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.hero-title {
    font-family: 'DM Serif Display', serif !important;
    font-size: 2.6rem !important; color: var(--dtu-red) !important;
    margin: 0 !important; letter-spacing: 0.02em; line-height: 1.2;
}
.hero-subtitle {
    font-family: 'Source Sans 3', sans-serif !important; font-size: 1.1rem;
    color: var(--text-color); opacity: 0.6;
    margin-top: 0.5rem; font-weight: 300;
    letter-spacing: 0.04em; text-transform: uppercase;
}
.hero-acronym {
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.75rem;
    color: var(--text-color); opacity: 0.45;
    margin-top: 0.3rem; letter-spacing: 0.08em;
}

/* ── Textarea ────────────────────────────────────────────────────── */
.stTextArea textarea {
    font-family: 'Source Sans 3', sans-serif !important; font-size: 1.05rem !important;
    color: var(--text-color) !important; -webkit-text-fill-color: var(--text-color) !important;
    border: 2px solid var(--secondary-background-color) !important;
    border-radius: var(--radius) !important;
    background: var(--background-color) !important; padding: 1rem !important;
    caret-color: var(--text-color) !important;
}
.stTextArea textarea::placeholder {
    color: var(--text-color) !important; opacity: 0.4 !important;
    -webkit-text-fill-color: var(--text-color) !important;
}
.stTextArea textarea:focus {
    border-color: var(--dtu-red) !important;
    box-shadow: 0 0 0 3px rgba(153,0,0,0.12) !important;
}
.stTextInput input {
    color: var(--text-color) !important; -webkit-text-fill-color: var(--text-color) !important;
}

/* ═══════════════════════════════════════════════════════════════════
   ALL SECONDARY BUTTONS — theme-aware colors
   ═══════════════════════════════════════════════════════════════════ */
.stButton button:not([kind="primary"]) {
    background: var(--secondary-background-color) !important;
    color: var(--text-color) !important;
    -webkit-text-fill-color: var(--text-color) !important;
    border: 1px solid color-mix(in srgb, var(--text-color) 15%, transparent) !important;
    border-radius: 8px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    white-space: normal !important; word-wrap: break-word !important;
    height: auto !important; min-height: 2.4rem !important;
    text-align: left !important; line-height: 1.45 !important;
    padding: 0.5rem 0.9rem !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
}
.stButton button:not([kind="primary"]) p,
.stButton button:not([kind="primary"]) span {
    color: var(--text-color) !important;
    -webkit-text-fill-color: var(--text-color) !important;
}
.stButton button:not([kind="primary"]):hover {
    border-color: var(--dtu-red) !important;
    color: var(--dtu-red) !important;
    -webkit-text-fill-color: var(--dtu-red) !important;
}
.stButton button:not([kind="primary"]):hover p,
.stButton button:not([kind="primary"]):hover span {
    color: var(--dtu-red) !important;
    -webkit-text-fill-color: var(--dtu-red) !important;
}

/* ── Result cards — theme-aware ──────────────────────────────────── */
.advisor-card {
    background: var(--background-color);
    border: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
    border-radius: var(--radius); padding: 1.5rem 1.8rem; margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); position: relative; overflow: hidden;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.advisor-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-1px); }
.advisor-card::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 4px; height: 100%; background: var(--dtu-red);
}
.advisor-rank {
    font-family: 'DM Serif Display', serif; font-size: 1.8rem;
    color: var(--oracle-gold); position: absolute; top: 1rem; right: 1.5rem; opacity: 0.5;
}
.advisor-header { display: flex; gap: 1.2rem; align-items: flex-start; }
.advisor-photo {
    width: 86px; height: 86px; border-radius: 50%; object-fit: cover;
    border: 3px solid var(--oracle-gold); flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.advisor-photo-placeholder {
    width: 86px; height: 86px; border-radius: 50%; flex-shrink: 0;
    background: var(--dtu-red); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-family: 'DM Serif Display', serif; font-size: 1.8rem;
    border: 3px solid var(--oracle-gold);
}
.advisor-name {
    font-family: 'DM Serif Display', serif !important; font-size: 1.35rem;
    color: var(--text-color) !important; margin: 0 0 0.15rem 0;
}
.advisor-title-line {
    font-size: 0.9rem; color: var(--text-color) !important; opacity: 0.6;
    margin-bottom: 0.6rem; font-weight: 400;
}
.advisor-section-badge {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 99px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
    text-transform: uppercase;
    background: var(--secondary-background-color);
    color: var(--text-color); opacity: 0.7;
    margin-right: 0.5rem;
}
.match-score {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 99px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
    font-family: 'JetBrains Mono', monospace;
}
.score-high { background: #e8f5e9; color: #2d6e3a; }
.score-mid  { background: #fff8e1; color: #8a6914; }
.score-low  { background: #fff0e0; color: #8a5014; }
.role-tag {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 99px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
}
.role-supervisor    { background: #e8f0fb; color: #1f4e8c; }
.role-co-supervisor { background: #f3e8fb; color: #6a2d8c; }
.match-explanation {
    margin-top: 0.8rem; padding: 0.8rem 1rem;
    background: var(--secondary-background-color);
    border-radius: 8px; font-size: 0.92rem; line-height: 1.6;
    color: var(--text-color) !important;
}
.advisor-links a {
    color: var(--dtu-red) !important; text-decoration: none;
    font-size: 0.88rem; font-weight: 500;
}
.advisor-links a:hover { text-decoration: underline; }

/* ── Co-supervisor suggestion strip ──────────────────────────────── */
.cosup-strip {
    margin-top: 0.9rem; padding-top: 0.8rem;
    border-top: 1px dashed color-mix(in srgb, var(--text-color) 15%, transparent);
}
.cosup-label {
    font-size: 0.78rem; font-weight: 600; color: var(--dtu-red);
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.5rem;
}
.cosup-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.cosup-chip {
    display: flex; align-items: center; gap: 0.5rem;
    background: var(--secondary-background-color);
    border-radius: 99px; padding: 0.25rem 0.9rem 0.25rem 0.25rem;
    font-size: 0.82rem; color: var(--text-color);
    text-decoration: none !important;
    border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
    transition: border-color 0.15s ease;
}
.cosup-chip:hover { border-color: var(--dtu-red); }
.cosup-chip-main {
    border: 2px solid #1f4e8c;
    background: color-mix(in srgb, #1f4e8c 8%, var(--secondary-background-color));
}
.cosup-chip-main .cosup-name { color: #1f4e8c; }
.cosup-note {
    font-size: 0.78rem; opacity: 0.65; color: var(--text-color);
    margin-bottom: 0.5rem; line-height: 1.5; font-style: italic;
}
.cosup-photo {
    width: 34px; height: 34px; border-radius: 50%; object-fit: cover;
    border: 2px solid var(--oracle-gold);
}
.cosup-photo-placeholder {
    width: 34px; height: 34px; border-radius: 50%;
    background: var(--dtu-red); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 600;
    border: 2px solid var(--oracle-gold);
}
.cosup-name { font-weight: 600; }
.cosup-meta { opacity: 0.6; font-size: 0.74rem; }

/* ── Agentic pipeline trace ──────────────────────────────────────── */
.agent-step {
    display: flex; gap: 0.8rem; align-items: flex-start;
    padding: 0.45rem 0;
}
.agent-step-num {
    width: 1.6rem; height: 1.6rem; border-radius: 50%; flex-shrink: 0;
    background: var(--dtu-red); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600;
}
.agent-step-title { font-weight: 600; font-size: 0.9rem; color: var(--text-color); }
.agent-step-detail { font-size: 0.85rem; opacity: 0.7; color: var(--text-color); line-height: 1.5; }

/* ── Profile details — pure HTML collapsible, theme-aware ────────── */
.oracle-details {
    background: var(--background-color);
    border: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
    border-radius: var(--radius); margin-bottom: 1rem; overflow: hidden;
}
.oracle-details summary {
    padding: 0.75rem 1.2rem; cursor: pointer;
    font-family: 'Source Sans 3', sans-serif; font-size: 0.95rem; font-weight: 600;
    color: var(--text-color); background: var(--background-color);
    list-style: none; display: flex; align-items: center; gap: 0.5rem;
    user-select: none; transition: background 0.15s ease;
}
.oracle-details summary:hover { background: var(--secondary-background-color); }
.oracle-details summary::before {
    content: ''; display: inline-block; width: 0.45rem; height: 0.45rem;
    border-right: 2px solid currentColor; border-bottom: 2px solid currentColor;
    transform: rotate(-45deg); transition: transform 0.2s ease; flex-shrink: 0;
    opacity: 0.5;
}
.oracle-details[open] summary::before { transform: rotate(45deg); }
.oracle-details summary::-webkit-details-marker { display: none; }
.oracle-details summary::marker { display: none; content: ''; font-size: 0; }
.oracle-details .details-body {
    padding: 0.5rem 1.2rem 1rem 1.2rem;
    border-top: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
    color: var(--text-color); font-size: 0.92rem; line-height: 1.65;
}
/* Field labels inside profile cards */
.field-label {
    font-weight: 600; color: var(--dtu-red); font-size: 0.82rem;
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.3rem;
}
.profile-list {
    margin: 0; padding-left: 1.2rem; font-size: 0.88rem;
    color: var(--text-color); line-height: 1.7;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] h1 {
    font-size: 1.1rem !important; color: var(--dtu-red) !important;
}

/* ── Footer ──────────────────────────────────────────────────────── */
.oracle-footer {
    text-align: center; padding: 2rem 0 1rem 0;
    border-top: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
    margin-top: 3rem; font-size: 0.8rem;
    color: var(--text-color); opacity: 0.45;
}

/* ── Scroll-to-top ───────────────────────────────────────────────── */
.scroll-top-btn {
    position: fixed; bottom: 2rem; right: 2rem;
    width: 44px; height: 44px; border-radius: 50%;
    background: var(--dtu-red); color: #fff !important; border: none;
    cursor: pointer; font-size: 1.2rem;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    opacity: 0; pointer-events: none;
    transition: opacity 0.3s ease, transform 0.2s ease; z-index: 9999;
}
.scroll-top-btn.visible { opacity: 1; pointer-events: auto; }
.scroll-top-btn:hover { transform: scale(1.1); }
</style>
""", unsafe_allow_html=True)


# ── Scroll-to-top JS + force light theme on load ──────────────────────
st.markdown("""
<button class="scroll-top-btn" id="scrollTopBtn" onclick="scrollToTop()" title="Back to top">&#9650;</button>
<script>
/* Force light mode: clear any cached dark theme preference */
try {
    var keys = Object.keys(localStorage);
    for (var i = 0; i < keys.length; i++) {
        if (keys[i].indexOf('theme') !== -1 || keys[i].indexOf('Theme') !== -1) {
            localStorage.removeItem(keys[i]);
        }
    }
} catch(e) {}

function checkScroll() {
    var btn = document.getElementById('scrollTopBtn');
    if (!btn) return;
    if ((window.scrollY || document.documentElement.scrollTop || 0) > 400)
        btn.classList.add('visible');
    else btn.classList.remove('visible');
}
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
window.addEventListener('scroll', checkScroll);
setInterval(checkScroll, 500);
</script>
""", unsafe_allow_html=True)


# ── Search engine ───────────────────────────────────────────────────────
@st.cache_resource
def load_engine(eligible_only: bool):
    from search_engine import OracleSearchEngine
    return OracleSearchEngine(available_only=eligible_only)


@st.cache_resource
def corpus_stats():
    from advisors_data import get_available_advisors, get_supervisors, get_co_supervisors
    return {
        "total": len(get_available_advisors()),
        "supervisors": len(get_supervisors()),
        "co_supervisors": len(get_co_supervisors()),
    }


# ── HTML rendering helper ───────────────────────────────────────────────
_WS_RE = re.compile(r"\n\s*")


def st_html(html: str):
    """
    Render generated HTML reliably. Markdown treats indented lines as
    code blocks, so multi-line f-string HTML can show up as raw text —
    collapse all newlines + indentation into single spaces first.
    """
    st.markdown(_WS_RE.sub(" ", html), unsafe_allow_html=True)


def md_bold_to_html(text: str) -> str:
    """Escape text for HTML, then convert **markdown bold** to <strong>."""
    escaped = html_module.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped.replace("\n", "<br>")


# ── Photo helpers — embed local photos as base64 data URIs ─────────────
@st.cache_data(max_entries=512)
def photo_data_uri(photo_path: str):
    """Read a local advisor photo and return it as a base64 data URI."""
    if not photo_path:
        return None
    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), photo_path)
    if not os.path.exists(abs_path):
        return None
    with open(abs_path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def photo_html(advisor: dict, css_class: str, placeholder_class: str) -> str:
    """
    Return an <img> tag for the advisor photo (photos/<orcid>.jpg), or a
    question-mark placeholder when no portrait is available.
    """
    uri = photo_data_uri(advisor.get("photo"))
    name = html_module.escape(advisor["name"])
    if uri:
        return f'<img class="{css_class}" src="{uri}" alt="{name}">'
    return f'<div class="{placeholder_class}" title="No photo available">?</div>'


def role_badge(advisor: dict) -> str:
    if advisor["role"] == "supervisor":
        return '<span class="role-tag role-supervisor">🎓 Main supervisor</span>'
    return '<span class="role-tag role-co-supervisor">🤝 Co-supervisor</span>'


# ── Sidebar ─────────────────────────────────────────────────────────────
stats = corpus_stats()

with st.sidebar:
    st.markdown("# ⚙️ Search Settings")
    st.markdown("---")
    top_k = st.slider("Number of results", min_value=1, max_value=15, value=5,
                       help="How many advisor recommendations to return")
    eligible_only = st.toggle("Eligible advisors only", value=True,
                               help="Exclude emeritus / retired / administrative staff")
    show_trace = st.toggle("Show agentic pipeline", value=True,
                            help="Display the step-by-step reasoning trace of the "
                                 "Oracle's agentic retrieval pipeline inside the results")
    live_explore = st.toggle("🌐 Explore the DTU net", value=True,
                              help="Agentic exploration: live-search the public DTU "
                                   "Orbit portal (orbit.dtu.dk) for additional researchers "
                                   "matching your query and grow the supervisor list")
    st.markdown("---")
    st.markdown("# 🔑 RAG Explanations")
    st.markdown(
        """<div style="font-size: 0.82rem; opacity: 0.7; margin-bottom: 0.5rem;">
        Get a <strong>free</strong> API key at
        <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com/apikey</a>
        — no credit card required.
        </div>""",
        unsafe_allow_html=True,
    )
    # Pre-fill from .streamlit/secrets.toml (gitignored) or env var —
    # never hardcode API keys in source.
    _default_key = os.environ.get("GEMINI_API_KEY", "")
    try:
        _default_key = st.secrets.get("GEMINI_API_KEY", _default_key)
    except Exception:
        pass
    api_key = st.text_input("Google Gemini API Key", type="password",
                             value=_default_key,
                             help="Free: get yours at aistudio.google.com/apikey — "
                                  "or store it in .streamlit/secrets.toml as GEMINI_API_KEY",
                             placeholder="AIza...")
    use_rag = st.toggle("Enable RAG explanations", value=bool(api_key),
                         disabled=not bool(api_key),
                         help="Use Gemini to generate natural-language match explanations")
    st.markdown("---")
    st.markdown("# 📊 Data Sources")
    st.markdown(f"""Current index covers **{stats['total']:,} DTU researchers**
({stats['supervisors']:,} potential supervisors,
{stats['co_supervisors']:,} potential co-supervisors) from:
- DTU Orbit profiles & publications
- ORCID public records
- Wikidata researcher entities
- Staff photos & AI-generated research summaries""")
    st.markdown("---")
    st.markdown("# 🧬 Extend the Oracle")
    with st.expander("Embedding-based search — how it works"):
        st.markdown("""
**Want richer, meaning-aware matching?** The Oracle can be upgraded
from TF-IDF keyword search to **embedding-based semantic search**.
The procedure:

**1. Scrape more supervisors**
Crawl `orbit.dtu.dk` (or `people.compute.dtu.dk`) for staff pages,
collect names + ORCID iDs into `dtu_staff_orcids.json`.

**2. Enrich each profile**
Query the ORCID public API and Wikidata for publications, abstracts,
photos, and fingerprint concepts → `dtu_supervisors.json` →
`advisors_enriched.json` (adds AI summaries & pitches).

**3. Embed the profiles**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(
    [build_advisor_document(a) for a in advisors]
)
```

**4. Index & search**
Store the vectors in a FAISS index and replace the TF-IDF
ranking in `search_engine.py` with nearest-neighbour search —
queries then match by *meaning*, not just shared keywords.

**5. (Optional) Agentic RAG**
Let an LLM agent re-rank the top candidates, explain matches,
and propose supervisor + co-supervisor teams — as previewed
in the 🤖 pipeline trace shown with every search.
""")
    st.markdown("---")
    st.caption("**ORACLE of Lyngby** · DTU Compute Retreat 2026 · Built with agentic coding")


# ── Hero ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-container">
    <div class="hero-icon">🏛️</div>
    <div class="hero-title">The ORACLE of Lyngby</div>
    <div class="hero-subtitle">Find Your Thesis Advisor at DTU</div>
    <div class="hero-acronym">Open Retrieval of Advisors by Course and Literature Expertise</div>
</div>""", unsafe_allow_html=True)


# ── State ───────────────────────────────────────────────────────────────
EXAMPLES = [
    "I want to work on eye tracking and reading behavior analysis using machine learning",
    "I'm interested in fairness and bias in medical AI systems",
    "I want to do my thesis on GPU-accelerated numerical simulations",
    "I'm looking for someone who works on NLP and brain-computer interfaces",
    "I want to explore TinyML and deploy models on embedded IoT devices",
    "I'm interested in formal verification and automated theorem proving",
    "I want to work on diffusion models for image generation and restoration",
    "I'm interested in Bayesian statistics and probabilistic modeling",
    "I want to study trust and security in IoT systems",
    "I want to do time series forecasting for energy systems",
    "I'm interested in wind energy and turbine aerodynamics",
    "I want to work on quantum technologies and photonics",
]

if "query" not in st.session_state:
    st.session_state.query = ""
if "show_examples" not in st.session_state:
    st.session_state.show_examples = True
if "show_about" not in st.session_state:
    st.session_state.show_about = False
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "agent_trace" not in st.session_state:
    st.session_state.agent_trace = None
if "rag_text" not in st.session_state:
    st.session_state.rag_text = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "dtu_discoveries" not in st.session_state:
    st.session_state.dtu_discoveries = None


# ── Search input ────────────────────────────────────────────────────────
st.markdown(f"""
<p style="font-size: 1.02rem; color: var(--text-color); opacity: 0.6; max-width: 680px;
margin: 0 auto 1rem auto; text-align: center; line-height: 1.6;">
Describe your thesis idea, research interests, or the kind of
expertise you're looking for. ORACLE will search {stats['total']:,} DTU
researchers and propose supervisor + co-supervisor teams that
align best with your project.
</p>""", unsafe_allow_html=True)

query = st.text_area(
    "query_input",
    value=st.session_state.query,
    height=100,
    placeholder="e.g.  I want to investigate how typography affects reading comprehension using eye-tracking and cognitive load measurements...",
    label_visibility="collapsed",
)

col_btn, col_spacer = st.columns([1, 3])
with col_btn:
    search_clicked = st.button("🏛️  Consult the Oracle", type="primary", use_container_width=True)

# ── Example queries ─────────────────────────────────────────────────────
if st.button(
    "▾ Hide example queries" if st.session_state.show_examples else "▸ Show example queries",
    key="toggle_examples",
):
    st.session_state.show_examples = not st.session_state.show_examples
    st.rerun()

if st.session_state.show_examples:
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state.query = ex
                st.rerun()


# ── Search — store results in session_state so they survive reruns ──────
if search_clicked and query.strip():
    engine = load_engine(eligible_only)

    with st.spinner("The Oracle is consulting the archives of Lyngby..."):
        response = engine.search(query.strip(), top_k=top_k)
        st.session_state.search_results = response["results"]
        st.session_state.agent_trace = response["agent_trace"]
        st.session_state.last_query = query.strip()
        time.sleep(0.4)

    # ── Agentic DTU-net exploration — live-search orbit.dtu.dk ──────────
    st.session_state.dtu_discoveries = None
    if live_explore:
        from dtu_agent import explore_dtu_net
        with st.spinner("The Oracle is exploring the DTU net for more researchers..."):
            found, status = explore_dtu_net(query.strip())
        known_ids = {a["orcid_id"] for a in engine.advisors}
        known_names = {a["name"].lower() for a in engine.advisors}
        for f in found:
            f["known"] = (f["orcid_id"] in known_ids
                          or f["name"].lower() in known_names)
        n_new = sum(1 for f in found if not f["known"])
        st.session_state.dtu_discoveries = found
        st.session_state.agent_trace.insert(-1, {
            "step": "Explore DTU net",
            "detail": f"{status} {n_new} not yet in the local index.",
        })

    st.session_state.rag_text = None
    if use_rag and api_key and st.session_state.search_results:
        with st.spinner("Generating AI-powered match explanations..."):
            from search_engine import generate_rag_explanation
            st.session_state.rag_text = generate_rag_explanation(
                query, st.session_state.search_results, api_key
            )

elif search_clicked:
    st.warning("Please describe your thesis idea or research interests.")
    st.session_state.search_results = None
    st.session_state.agent_trace = None


# ── Display results — always renders from session_state ────────────────
if st.session_state.search_results is not None:
    results = st.session_state.search_results
    agent_trace = st.session_state.agent_trace
    rag_text = st.session_state.rag_text

    if not results:
        st.info("The Oracle found no matching advisors. Try broadening your description.")
    else:
        st.markdown(f"### Top {len(results)} Advisor{'s' if len(results) > 1 else ''} for Your Query")

        # ── Agentic pipeline trace — how the Oracle reasoned ───────────
        if show_trace and agent_trace:
            steps_html = ""
            for i, s in enumerate(agent_trace, 1):
                steps_html += f"""
                <div class="agent-step">
                    <div class="agent-step-num">{i}</div>
                    <div>
                        <div class="agent-step-title">{html_module.escape(s['step'])}</div>
                        <div class="agent-step-detail">{html_module.escape(s['detail'])}</div>
                    </div>
                </div>"""
            st_html(f"""
            <details class="oracle-details" open>
                <summary>🤖 Agentic pipeline — how the Oracle reasoned</summary>
                <div class="details-body">{steps_html}</div>
            </details>
            """)

        if rag_text:
            st.markdown("#### 🧠 AI-Powered Analysis (RAG)")
            st.markdown(rag_text)
            st.markdown("---")

        from search_engine import generate_match_explanation

        for rank, result in enumerate(results, 1):
            advisor = result["advisor"]
            score = result["score"]

            score_cls = "score-high" if score > 0.3 else ("score-mid" if score > 0.15 else "score-low")
            explanation_html = md_bold_to_html(generate_match_explanation(result))

            # ── Links: Orbit, ORCID, Wikidata ───────────────────────────
            links = []
            if advisor.get("orbit_url"):
                links.append(f'<a href="{advisor["orbit_url"]}" target="_blank">📚 Orbit profile</a>')
            if advisor.get("orcid_url"):
                links.append(f'<a href="{advisor["orcid_url"]}" target="_blank">🆔 ORCID</a>')
            if advisor.get("wikidata_id"):
                links.append(f'<a href="https://www.wikidata.org/wiki/{advisor["wikidata_id"]}" target="_blank">🌐 Wikidata</a>')
            links_html = " &nbsp;·&nbsp; ".join(links)

            # ── Supervision team suggestions with photos ────────────────
            # DTU rule: postdocs / research assistants / PhD students can't
            # be main supervisor — their team includes a professor-level
            # colleague (preferably same section) as proposed main supervisor.
            cosup_html = ""
            if result.get("team"):
                chips = ""
                for member in result["team"]:
                    ca = member["advisor"]
                    is_main = member["proposed_role"] == "main supervisor"
                    c_name = html_module.escape(ca["name"])
                    c_title = html_module.escape(ca["title"])
                    c_url = ca.get("orbit_url") or ca.get("orcid_url") or "#"
                    chip_cls = "cosup-chip cosup-chip-main" if is_main else "cosup-chip"
                    role_label = "🎓 Proposed main supervisor" if is_main else "🤝 Co-supervisor"
                    chips += f"""
                    <a class="{chip_cls}" href="{c_url}" target="_blank" title="{c_title} — {html_module.escape(ca['section'])}">
                        {photo_html(ca, 'cosup-photo', 'cosup-photo-placeholder')}
                        <span><span class="cosup-name">{c_name}</span><br>
                        <span class="cosup-meta">{role_label} · {c_title} · {member['score']:.0%} profile overlap</span></span>
                    </a>"""

                if advisor["role"] != "supervisor":
                    strip_label = "🎓 Suggested supervision team"
                    strip_note = ('<div class="cosup-note">Postdocs, research assistants and '
                                  'PhD students cannot act as main supervisor of an MSc thesis — '
                                  'this team includes a professor-level main supervisor.</div>')
                else:
                    strip_label = "🤝 Suggested co-supervisors"
                    strip_note = ""
                cosup_html = f"""
                <div class="cosup-strip">
                    <div class="cosup-label">{strip_label}</div>
                    {strip_note}
                    <div class="cosup-row">{chips}</div>
                </div>"""

            interests_html = "".join(
                f"<li>{html_module.escape(i)}</li>" for i in advisor["research_interests"][:10]
            ) or "<li><em>No indexed interests</em></li>"
            pubs_html = "".join(
                f"<li><em>{html_module.escape(p)}</em></li>" for p in advisor["recent_publications"]
            ) or "<li><em>No indexed publications</em></li>"
            summary_block = (
                f'<div class="field-label" style="margin-top: 0.8rem;">Research Summary</div>'
                f'<div style="font-size: 0.88rem; line-height: 1.6;">{html_module.escape(advisor["summary"])}</div>'
            ) if advisor.get("summary") else ""

            full_card = f"""
            <div class="advisor-card">
                <div class="advisor-rank">#{rank}</div>
                <div class="advisor-header">
                    {photo_html(advisor, 'advisor-photo', 'advisor-photo-placeholder')}
                    <div style="flex: 1; min-width: 0;">
                        <div class="advisor-name">{html_module.escape(advisor['name'])}</div>
                        <div class="advisor-title-line">
                            {html_module.escape(advisor['title'])} &nbsp;·&nbsp; {html_module.escape(advisor['department'])}
                        </div>
                        <div style="margin-bottom: 0.6rem;">
                            <span class="advisor-section-badge">{html_module.escape(advisor['section'])}</span>
                            <span class="match-score {score_cls}">match: {score:.0%}</span>
                            {role_badge(advisor)}
                        </div>
                    </div>
                </div>
                <div class="match-explanation">
                    {explanation_html}
                </div>
                {cosup_html}
                <div class="advisor-links" style="margin-top: 0.8rem;">
                    {links_html}
                </div>
            </div>
            <details class="oracle-details">
                <summary>📋 Full profile — {html_module.escape(advisor['name'])}</summary>
                <div class="details-body">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                        <div>
                            <div class="field-label">Research Interests / Fingerprint Concepts</div>
                            <ul class="profile-list">{interests_html}</ul>
                        </div>
                        <div>
                            <div class="field-label">Recent Publications</div>
                            <ul class="profile-list">{pubs_html}</ul>
                        </div>
                    </div>
                    {summary_block}
                </div>
            </details>
            """
            st_html(full_card)

        # ── Live DTU-net discoveries — agentic supervisor-list update ──
        discoveries = st.session_state.dtu_discoveries
        if discoveries is not None:
            st.markdown("#### 🌐 Live DTU-net discoveries")
            if not discoveries:
                st.caption("The DTU-net exploration agent found no additional "
                           "researchers for this query (or orbit.dtu.dk was unreachable).")
            else:
                lines = []
                for f in discoveries:
                    tag = "✓ already indexed" if f["known"] else "🆕 **new**"
                    lines.append(f"- [{f['name']}]({f['orcid_url']}) — {tag}")
                st.markdown("\n".join(lines))

                new_found = [f for f in discoveries if not f["known"]]
                if new_found:
                    if st.button(
                        f"➕ Add {len(new_found)} new researcher"
                        f"{'s' if len(new_found) != 1 else ''} to the Oracle's supervisor list",
                        key="add_discovered",
                    ):
                        from dtu_agent import save_discovered
                        import advisors_data
                        added = save_discovered(new_found, st.session_state.last_query)
                        advisors_data.reload()
                        load_engine.clear()
                        corpus_stats.clear()
                        st.success(
                            f"Added {added} researcher{'s' if added != 1 else ''} "
                            f"to dtu_discovered.json — the index now includes them. "
                            f"Run your search again to see the updated list."
                        )


# ── About Section ───────────────────────────────────────────────────────
st.markdown("---")

if st.button(
    "▾ ℹ️ About ORACLE" if st.session_state.show_about else "▸ ℹ️ About ORACLE",
    key="toggle_about",
):
    st.session_state.show_about = not st.session_state.show_about
    st.rerun()

if st.session_state.show_about:
    st.markdown(f"""
**The ORACLE of Lyngby** _(Open Retrieval of Advisors by Course
and Literature Expertise)_ helps Master's students at DTU discover
the right thesis supervisor **and co-supervisor**.

**How it works (agentic pipeline):**

1. You describe your thesis idea or research interests in free text.
2. The Oracle's agent **parses** your query, **retrieves** matching
   profiles from {stats['total']:,} DTU researchers (research fingerprints,
   AI summaries, publications + abstracts) using TF-IDF similarity,
   and **ranks** them by relevance.
3. For each recommended supervisor it **matches co-supervisors** by
   profile similarity, building complete supervision teams.
4. Every step is shown in the 🤖 pipeline trace inside the results.
5. _(Optional)_ With a free Google Gemini API key, ORACLE generates richer,
   AI-powered explanations using retrieval-augmented generation (RAG).

**Data sources indexed:** DTU Orbit profiles and publications,
ORCID public records, Wikidata researcher entities, staff photos,
and AI-generated research summaries — {stats['total']:,} researchers,
{stats['supervisors']:,} potential supervisors and
{stats['co_supervisors']:,} potential co-supervisors across all DTU departments.

**Architecture:** TF-IDF + cosine similarity baseline (Approach 1–2),
with optional RAG layer (Approach 3). See **🧬 Extend the Oracle** in
the sidebar for the embedding-based search upgrade procedure.

---

_Built at the DTU Compute Retreat 2026 · Hackathon: "Have Anarchic
Fun with Agentic Coding"_
""")


# ── Footer ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="oracle-footer">
    The ORACLE of Lyngby &nbsp;·&nbsp; DTU Compute Retreat 2026
    &nbsp;·&nbsp; "Have Anarchic Fun with Agentic Coding"<br>
    <em>Occasionally Reliable Academic Compass for Lost Examinees</em>
</div>""", unsafe_allow_html=True)
