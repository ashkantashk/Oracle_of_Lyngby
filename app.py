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
"""

import streamlit as st
import time
import html as html_module

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
.availability-tag {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 99px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
}
.avail-ok      { background: #e8f5e9; color: #2d6e3a; }
.avail-limited { background: #fff8e1; color: #8a6914; }
.avail-full    { background: #fce4e4; color: #8a2020; }
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
def load_engine(available_only: bool):
    from search_engine import OracleSearchEngine
    return OracleSearchEngine(available_only=available_only)


# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚙️ Search Settings")
    st.markdown("---")
    top_k = st.slider("Number of results", min_value=1, max_value=15, value=5,
                       help="How many advisor recommendations to return")
    available_only = st.toggle("Available advisors only", value=True,
                                help="Exclude advisors at full capacity or unavailable")
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
    api_key = st.text_input("Google Gemini API Key", type="password",
                             help="Free: get yours at aistudio.google.com/apikey",
                             placeholder="AIza...")
    use_rag = st.toggle("Enable RAG explanations", value=bool(api_key),
                         disabled=not bool(api_key),
                         help="Use Claude to generate natural-language match explanations")
    st.markdown("---")
    st.markdown("# 📊 Data Sources")
    st.markdown("""Current index covers **19 advisors** from:
- DTU Compute staff profiles
- DTU Orbit publications
- Kursusbasen course catalog
- Supervised thesis records""")
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
]

if "query" not in st.session_state:
    st.session_state.query = ""
if "show_examples" not in st.session_state:
    st.session_state.show_examples = True
if "show_about" not in st.session_state:
    st.session_state.show_about = False
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "rag_text" not in st.session_state:
    st.session_state.rag_text = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""


# ── Search input ────────────────────────────────────────────────────────
st.markdown("""
<p style="font-size: 1.02rem; color: var(--text-color); opacity: 0.6; max-width: 680px;
margin: 0 auto 1rem auto; text-align: center; line-height: 1.6;">
Describe your thesis idea, research interests, or the kind of
expertise you're looking for. ORACLE will find the DTU researchers
whose work aligns best with yours.
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
    engine = load_engine(available_only)

    with st.spinner("The Oracle is consulting the archives of Lyngby..."):
        st.session_state.search_results = engine.search(query.strip(), top_k=top_k)
        st.session_state.last_query = query.strip()
        time.sleep(0.4)

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


# ── Display results — always renders from session_state ────────────────
if st.session_state.search_results is not None:
    results = st.session_state.search_results
    rag_text = st.session_state.rag_text

    if not results:
        st.info("The Oracle found no matching advisors. Try broadening your description.")
    else:
        st.markdown(f"### Top {len(results)} Advisor{'s' if len(results) > 1 else ''} for Your Query")

        if rag_text:
            st.markdown("#### 🤖 AI-Powered Analysis")
            st.markdown(rag_text)
            st.markdown("---")

        for rank, result in enumerate(results, 1):
            advisor = result["advisor"]
            score = result["score"]

            score_cls = "score-high" if score > 0.3 else ("score-mid" if score > 0.15 else "score-low")
            avail = advisor["availability"]
            if avail == "available":
                avail_cls = "avail-ok"
                avail_label = f"✓ Available ({advisor['current_students']}/{advisor['max_students']} students)"
            elif avail == "limited":
                avail_cls = "avail-limited"
                avail_label = f"⚠ Limited ({advisor['current_students']}/{advisor['max_students']} students)"
            else:
                avail_cls = "avail-full"
                avail_label = "✕ At capacity"

            from search_engine import generate_match_explanation
            explanation = generate_match_explanation(result)

            links_html = (
                f'<a href="{advisor["profile_url"]}" target="_blank">🌐 Profile</a>'
                f' &nbsp;·&nbsp; '
                f'<a href="{advisor["orbit_url"]}" target="_blank">📚 Orbit</a>'
                f' &nbsp;·&nbsp; '
                f'<a href="mailto:{advisor["email"]}">✉ {advisor["email"]}</a>'
            )

            interests_html = "".join(f"<li>{html_module.escape(i)}</li>" for i in advisor["research_interests"])
            courses_html = "".join(f"<li>{html_module.escape(c)}</li>" for c in advisor["courses"]) if advisor["courses"] else ""
            pubs_html = "".join(f"<li><em>{html_module.escape(p)}</em></li>" for p in advisor["recent_publications"])
            topics_html = "".join(f"<li>{html_module.escape(t)}</li>" for t in advisor["supervised_topics"])

            courses_block = f'<div class="field-label" style="margin-top: 0.8rem;">Courses</div><ul class="profile-list">{courses_html}</ul>' if courses_html else ''

            full_card = f"""
            <div class="advisor-card">
                <div class="advisor-rank">#{rank}</div>
                <div class="advisor-name">{advisor['name']}</div>
                <div class="advisor-title-line">
                    {advisor['title']} &nbsp;·&nbsp; {advisor['building']}
                </div>
                <div style="margin-bottom: 0.6rem;">
                    <span class="advisor-section-badge">{advisor['section']}</span>
                    <span class="match-score {score_cls}">match: {score:.0%}</span>
                    <span class="availability-tag {avail_cls}">{avail_label}</span>
                </div>
                <div class="match-explanation">
                    {explanation.replace(chr(10), '<br>')}
                </div>
                <div class="advisor-links" style="margin-top: 0.8rem;">
                    {links_html}
                </div>
            </div>
            <details class="oracle-details">
                <summary>📋 Full profile — {advisor['name']}</summary>
                <div class="details-body">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                        <div>
                            <div class="field-label">Research Interests</div>
                            <ul class="profile-list">{interests_html}</ul>
                            {courses_block}
                        </div>
                        <div>
                            <div class="field-label">Recent Publications</div>
                            <ul class="profile-list">{pubs_html}</ul>
                            <div class="field-label" style="margin-top: 0.8rem;">Past Thesis Topics</div>
                            <ul class="profile-list">{topics_html}</ul>
                        </div>
                    </div>
                </div>
            </details>
            """
            st.markdown(full_card, unsafe_allow_html=True)


# ── About Section ───────────────────────────────────────────────────────
st.markdown("---")

if st.button(
    "▾ ℹ️ About ORACLE" if st.session_state.show_about else "▸ ℹ️ About ORACLE",
    key="toggle_about",
):
    st.session_state.show_about = not st.session_state.show_about
    st.rerun()

if st.session_state.show_about:
    st.markdown("""
**The ORACLE of Lyngby** _(Open Retrieval of Advisors by Course
and Literature Expertise)_ helps Master's students at DTU discover
the right thesis advisor.

**How it works:**

1. You describe your thesis idea or research interests in free text.
2. ORACLE searches across advisor profiles, publications, course
   catalogues, and past thesis supervisions using TF-IDF similarity.
3. Results are ranked by relevance with explanations of why each
   advisor is a good fit.
4. _(Optional)_ With a free Google Gemini API key, ORACLE generates richer,
   AI-powered explanations using retrieval-augmented generation (RAG).

**Data sources indexed:** DTU Compute staff profiles
(`people.compute.dtu.dk`), DTU Orbit publications, Kursusbasen
course descriptions, and supervised thesis records.

**Architecture:** TF-IDF + cosine similarity baseline (Approach 1–2),
with optional RAG layer (Approach 3). Designed to be extended with
embedding-based search, knowledge graphs, or ensemble ranking.

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
