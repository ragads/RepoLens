# pages/guide.py
"""In-app walkthrough: what each section does, in the order you use them.

Screenshots live in assets/guide/ and are captured from the running app, so they
stay honest. If an image is missing the step still renders, just without a picture.
"""
from pathlib import Path

import streamlit as st

from components.cards import section_header

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "guide"


def _shot(name: str, caption: str = "") -> None:
    """Render a screenshot if it exists; stay quiet if it doesn't."""
    path = ASSETS / f"{name}.png"
    if path.exists():
        st.image(str(path), caption=caption or None, use_container_width=True)
    else:
        st.caption(f"_(screenshot `{name}.png` not found in assets/guide/)_")


def _step(num: int, title: str, blurb: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:baseline;gap:12px;margin-top:8px;">
          <span style="font-family:var(--font-mono);font-size:0.8rem;font-weight:600;
                color:var(--accent);">{num:02d}</span>
          <span style="font-size:1.0625rem;font-weight:650;
                color:var(--text-primary);">{title}</span>
        </div>
        <div style="color:var(--text-secondary);font-size:0.9375rem;
             margin:4px 0 12px 30px;">{blurb}</div>
        """,
        unsafe_allow_html=True,
    )


FLOW = """\
  github.com/owner/repo
          |
          |  branch ZIP over HTTPS  (public repos only, no token)
          v
  +-------------------------------------------------------------+
  |  filter                                                      |
  |    keep   .py .js .ts .md .json .yaml .html .css .java .go   |
  |    drop   dotfiles, node_modules/, venv/, binaries, >300 KB  |
  +-------------------------------------------------------------+
          |
          v
  +-------------------------------------------------------------+
  |  index                                                       |
  |    whole file            -->  assistant_files                |
  |    40-line chunks        -->  assistant_file_chunks          |
  |    (embeddings only when a Gemini key is present)            |
  +-------------------------------------------------------------+
          |
          +----------------+----------------+----------------+
          v                v                v                v
   Project Overview   Security Audit   Static Preview   Indexed Files
     README or AI      2-pass scan      inline CSS+JS     browse and
      explanation           |            into the HTML      delete
                            v
                     assistant_audits
                            |
                            v
                    Markdown  /  PDF
"""

AUDIT_FLOW = """\
  every indexed source file
          |
          v
  PASS A -- static heuristics        free, no cap, runs on EVERY file
  14 regex rules, line by line       language-gated to cut false positives
          |
          v
  prioritize  (cap: 40 files, 40 KB each)
    1. files with heuristic hits
    2. files near risky vector-search terms
    3. the rest, smallest first
    everything dropped is LOGGED, never silent
          |
          v
  PASS B -- LLM deep analysis        one call per file, strict JSON out
  seeded with that file's hits       a bad file is skipped, never aborts
          |
          v
  merge + dedup   key = (file, line, CWE)
    keep the heuristic's line number (LLM lines are approximate)
    take the LLM's description and fix
          |
          v
  score  =  max(0, 100 - (critical*20 + high*10 + medium*4 + low*1))
  grade  =  A >=90   B >=80   C >=70   D >=60   else F
"""


def render_guide() -> None:
    section_header(
        "Guide",
        "How to use DevPulse Architect, section by section, in the order you use them.",
    )

    st.markdown(
        '<div class="dp-overline" style="margin-bottom:10px">'
        "The whole app in one picture</div>",
        unsafe_allow_html=True,
    )
    _shot("00_app")
    st.caption(
        "Sidebar on the left, the active section on the right. Collapse the sidebar with "
        "« and reopen it with the » button that appears at the top-left."
    )

    st.markdown("---")

    # ── Data flow ────────────────────────────────────────────────────
    st.markdown('<div class="dp-overline">How data moves</div>', unsafe_allow_html=True)
    st.caption(
        "Everything lands in one local SQLite file, `assistant.db`. "
        "No code from the analyzed repository is ever executed."
    )
    st.code(FLOW, language="text")

    st.markdown("---")

    # ── Steps ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="dp-overline">Step by step</div>', unsafe_allow_html=True
    )
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    _step(1, "Ingest Repository — upload a codebase",
          "Paste a <b>public</b> GitHub URL, set the branch, and press "
          "<b>Analyze Repository</b>. The app downloads the branch ZIP, throws away "
          "binaries and dependency folders, and indexes every text file. A progress bar "
          "names each file as it goes.")
    _shot("01_ingest")
    with st.expander("What gets skipped, and why"):
        st.markdown(
            "- **Private repos** — no GitHub token is configured, so they're detected "
            "and refused up front.\n"
            "- **Dotfiles, `node_modules/`, `venv/`, `__pycache__/`** — noise.\n"
            "- **Files over 300 KB** — they blow up the context window.\n"
            "- **Images and binaries** — not text, nothing to analyze. This is why the "
            "Static Preview shows broken images.\n\n"
            "Branch defaults to `main` and falls back to `master` automatically."
        )
    st.markdown("---")

    _step(2, "Overview — confirm the ingest landed",
          "Counts of files, source files, embedded chunks and total size, plus a "
          "language breakdown. If this still says <i>Nothing indexed yet</i>, the "
          "ingest did not happen.")
    _shot("02_overview")
    st.markdown("---")

    _step(3, "Project Overview — understand what you just pulled in",
          "Shows the repository's README. If there isn't one, your selected model writes "
          "an explanation covering purpose, structure and architecture from the file tree "
          "and the first few key files.")
    _shot("03_project")
    st.info("This section needs an API key. Without one it will tell you so, rather than fail.")
    st.markdown("---")

    _step(4, "Security Audit — the main event",
          "Press <b>Run Security Audit</b>. You get severity tiles, a score out of 100, "
          "a letter grade, a filterable findings list, and Markdown + PDF export. "
          "The static rules run with <b>no API key at all</b>.")
    _shot("04_audit")

    st.markdown('<div class="dp-overline">How the audit works</div>', unsafe_allow_html=True)
    st.code(AUDIT_FLOW, language="text")

    st.markdown('<div class="dp-overline">Reading a finding</div>', unsafe_allow_html=True)
    st.caption(
        "Expand any row for the location, the offending snippet, and a concrete fix. "
        "Every finding names its source — `heuristic`, `llm`, or `both` — so you know "
        "how much to trust it."
    )
    _shot("05_finding")

    st.warning(
        "**Both passes produce false positives.** A regex cannot know that a SHA-1 call "
        "is a cache key rather than a password hash, and an LLM can misreport a line "
        "number. Read each finding before acting on it."
    )
    st.markdown("---")

    _step(5, "Static Preview — see the repo's frontend",
          "Pick an HTML file. Its stylesheets and scripts are inlined and rendered in a "
          "sandboxed frame. Nothing is executed on a server — no subprocess, no port, "
          "no tunnel.")
    _shot("06_preview")
    with st.expander("What works, what doesn't"):
        st.markdown(
            "| | |\n|---|---|\n"
            "| **Works** | Plain HTML/CSS/JS. Absolute CDN links still load — the frame "
            "runs in your browser. |\n"
            "| **Degraded** | Images and fonts are excluded at ingest, so they render "
            "broken. Each missing asset is listed, never dropped silently. |\n"
            "| **Won't work** | React/Vue apps that need a build step. The app detects "
            "them and points you at `dist/index.html` if the repo ships one. |\n"
        )
    st.markdown("---")

    _step(6, "Indexed Files — browse and prune",
          "Every stored file with its type, language and size. Filter by name, delete "
          "anything you don't want in the next audit.")
    _shot("07_files")
    st.markdown("---")

    _step(7, "Settings — pick a model, paste a key",
          "Choose a provider, choose a model, paste that provider's key, then press "
          "<b>Test connection</b>. Also holds the theme switch and the wipe-database "
          "danger zone.")
    _shot("08_settings")

    st.markdown('<div class="dp-overline">Providers and models</div>', unsafe_allow_html=True)
    st.markdown(
        "| Provider | Models | Env var fallback |\n"
        "|---|---|---|\n"
        "| Google Gemini | `gemini-2.5-flash` (default), `gemini-2.5-pro` | `GEMINI_API_KEY` |\n"
        "| Anthropic (Claude) | `claude-opus-4-8` (default), `claude-sonnet-5`, "
        "`claude-haiku-4-5` | `ANTHROPIC_API_KEY` |\n"
        "| OpenAI (GPT) | `gpt-4o` (default), `gpt-4o-mini` | `OPENAI_API_KEY` |\n"
    )
    st.caption(
        "Keys live in memory for this browser session only and are never written to disk. "
        "Leave the field empty and the app falls back to the environment variable — that's "
        "how you configure it on a host like Render."
    )

    with st.expander("Why semantic search asks for a Gemini key separately"):
        st.markdown(
            "Vector search is powered by Google's `text-embedding-004`, so it needs a "
            "**Gemini** key regardless of which provider you picked for chat. This is the "
            "one place the two are coupled.\n\n"
            "- **With a Gemini key** — chunks are embedded, and vector search focuses the "
            "audit's AI pass on the riskiest code.\n"
            "- **Without one** — chunks store `NULL` embeddings and search degrades to "
            "keyword matching. Nothing breaks; the audit still runs and still prioritizes "
            "by heuristic hits.\n\n"
            "When your chat provider isn't Gemini, Settings shows an optional second field "
            "just for the embeddings key."
        )

    st.markdown("---")

    # ── Troubleshooting ──────────────────────────────────────────────
    st.markdown('<div class="dp-overline">When something looks wrong</div>',
                unsafe_allow_html=True)
    st.markdown(
        "| Symptom | Cause and fix |\n"
        "|---|---|\n"
        "| **“Nothing indexed yet”** | Not an error — the database is empty. Ingest a repo. |\n"
        "| **Sidebar disappeared** | It collapsed. Click the `»` button at the top-left. |\n"
        "| **`ERR_CONNECTION_REFUSED`** | Streamlit isn't running, or is on another port. "
        "Restart it and use the port printed in the terminal. |\n"
        "| **Audit finds nothing** | Often correct. A static HTML demo genuinely has no "
        "Python injection flaws. Try a repo with server-side code. |\n"
        "| **“Only the free static rules will run”** | No API key resolved. Set one in "
        "Settings, or export the provider's env var. |\n"
        "| **“This repository is private”** | Correct — only public repos can be fetched. |\n"
        "| **PDF button disabled** | `fpdf2` isn't installed. Re-run "
        "`pip install -r requirements.txt`. |\n"
        "| **Keys gone after restart** | By design — in-memory only. Use env vars to persist. |\n"
    )

    st.markdown("---")
    st.caption(
        "Static analysis is advisory. It narrows where to look; it does not replace review."
    )
