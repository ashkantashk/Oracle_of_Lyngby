"""
generate_summaries.py
=====================
Adds a ``supervisor_summary`` field (~50 ±10 words) to every advisor in
ADVISORS and writes the result to a new Python file.

Usage
-----
# LLM-based summaries (recommended):
    python generate_summaries.py --api-key sk-ant-...

# Template-based summaries (no API key required):
    python generate_summaries.py --template

# Custom output path:
    python generate_summaries.py --api-key sk-ant-... --output my_advisors.py
"""

import argparse
import pprint
import sys
import textwrap

import requests

from advisors_data import ADVISORS

TARGET_WORDS = 50
TOLERANCE = 10
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_MODEL = "claude-haiku-4-5"


# ── LLM-based summary ───────────────────────────────────────────────────

def _build_prompt(advisor: dict) -> str:
    interests = ", ".join(advisor["research_interests"])
    topics = ", ".join(advisor["supervised_topics"])
    pubs = "; ".join(advisor["recent_publications"]) if advisor["recent_publications"] else "N/A"
    courses = "; ".join(advisor["courses"]) if advisor["courses"] else "N/A"
    return textwrap.dedent(f"""
        Write a single-paragraph summary of a DTU researcher's expertise for Master's students who hold a Bachelor's degree.
        Requirements:
        - Exactly {TARGET_WORDS} ±{TOLERANCE} words (count carefully).
        - Do NOT mention the researcher's name or any publication/paper titles.
        - Do NOT use academic jargon — write for a student with a Bachelor's degree.
        - Describe the research topics and what kinds of thesis projects they typically supervise.
        - No bullet points; plain prose only.
        - Return only the summary — no preamble, headers, or extra formatting.

        Section: {advisor['section']}
        Research interests: {interests}
        Courses taught: {courses}
        Research areas from publications: {pubs}
        Supervised thesis topics: {topics}
    """).strip()


def generate_summary_llm(advisor: dict, api_key: str) -> str:
    """Call Claude Haiku to produce a ~50-word summary."""
    resp = requests.post(
        _ANTHROPIC_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        },
        json={
            "model": _MODEL,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": _build_prompt(advisor)}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


# ── Template-based fallback ─────────────────────────────────────────────

def generate_summary_template(advisor: dict) -> str:
    """
    Rule-based ~50-word summary.  No API key required.
    Anonymized: no researcher name, no publication titles.
    Targeted at students with a Bachelor's degree.
    """
    section = advisor["section"]
    interests = advisor["research_interests"]

    if len(interests) >= 3:
        interest_str = f"{', '.join(interests[:-1])}, and {interests[-1]}"
    elif len(interests) == 2:
        interest_str = f"{interests[0]} and {interests[1]}"
    else:
        interest_str = interests[0] if interests else "various topics"

    parts = [
        f"This researcher works in the {section} section at DTU Compute, "
        f"focusing on {interest_str}."
    ]

    if advisor["recent_publications"]:
        # Extract topic keywords from the publication title rather than quoting it
        pub_words = advisor["recent_publications"][0].split()
        # Skip common stop words for a cleaner topic extraction
        stop = {"a", "an", "the", "of", "for", "and", "in", "on", "to",
                "with", "using", "by", "from", "at", "is", "are", "as",
                "that", "this", "via", "into", "based", "do", "not"}
        topic_words = [w for w in pub_words if w.lower().rstrip("—-") not in stop][:6]
        topic_hint = " ".join(topic_words).rstrip(",;.—-")
        parts.append(f"Active research areas include topics such as {topic_hint.lower()}.")

    topics = advisor["supervised_topics"]
    if topics:
        if len(topics) >= 2:
            parts.append(
                f"Thesis supervision covers areas such as {topics[0].lower()} "
                f"and {topics[1].lower()}."
            )
        else:
            parts.append(f"Thesis supervision focuses on {topics[0].lower()}.")

    summary = " ".join(parts)

    # Trim to stay within upper word bound
    words = summary.split()
    if len(words) > TARGET_WORDS + TOLERANCE:
        words = words[:TARGET_WORDS + TOLERANCE]
        summary = " ".join(words).rstrip(",;") + "."

    return summary


# ── Output writer ───────────────────────────────────────────────────────

def write_enriched_file(enriched: list[dict], output_path: str) -> None:
    """
    Write a new Python module with the same structure as advisors_data.py
    but with the ``supervisor_summary`` field added to every entry.
    """
    header = textwrap.dedent('''\
        """
        ORACLE of Lyngby — Advisor Database (enriched)
        ================================================
        Auto-generated by generate_summaries.py.
        Contains all original fields plus ``supervisor_summary``.
        Do not edit manually — re-run generate_summaries.py to regenerate.
        """

        ADVISORS = ''')

    formatted = pprint.pformat(enriched, width=100, sort_dicts=False)

    footer = textwrap.dedent('''


        def get_all_advisors():
            """Return full advisor list."""
            return ADVISORS


        def get_available_advisors():
            """Return only advisors who are not at capacity."""
            return [
                a for a in ADVISORS
                if a["availability"] != "unavailable"
                and a["current_students"] < a["max_students"]
            ]


        def get_sections():
            """Return unique sections."""
            return sorted(set(a["section"] for a in ADVISORS))
        ''')

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(header)
        fh.write(formatted)
        fh.write(footer)


# ── Main ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate supervisor_summary fields for all advisors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Anthropic API key (uses claude-haiku for generation)",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Use rule-based summaries instead of LLM (no API key required)",
    )
    parser.add_argument(
        "--output",
        default="advisors_data_enriched.py",
        help="Output Python file path (default: advisors_data_enriched.py)",
    )
    args = parser.parse_args()

    use_llm = bool(args.api_key) and not args.template

    if not use_llm and not args.template:
        parser.error(
            "Provide --api-key for LLM summaries or --template for rule-based summaries."
        )

    print(
        f"Generating summaries for {len(ADVISORS)} advisors "
        f"using {'LLM (claude-haiku-4-5)' if use_llm else 'template'} ...\n"
    )

    enriched = []
    errors = []

    for advisor in ADVISORS:
        name = advisor["name"]
        print(f"  {name} ... ", end="", flush=True)
        try:
            if use_llm:
                summary = generate_summary_llm(advisor, args.api_key)
            else:
                summary = generate_summary_template(advisor)

            word_count = len(summary.split())
            flag = "" if abs(word_count - TARGET_WORDS) <= TOLERANCE else "  ⚠ out of range"
            print(f"{word_count} words{flag}")

            enriched.append({**advisor, "supervisor_summary": summary})

        except requests.HTTPError as exc:
            print(f"HTTP error: {exc}")
            errors.append(name)
            enriched.append({**advisor, "supervisor_summary": ""})
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}")
            errors.append(name)
            enriched.append({**advisor, "supervisor_summary": ""})

    print(f"\nWriting → {args.output}")
    write_enriched_file(enriched, args.output)
    print(f"Done.  {len(enriched) - len(errors)}/{len(ADVISORS)} summaries generated successfully.")

    if errors:
        print(f"\nFailed advisors: {', '.join(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
