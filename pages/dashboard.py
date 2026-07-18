# pages/dashboard.py
"""UI sections for DevPulse Architect.

Contains GitHub ingestion, repository overview, and AI Codebase Chat.
"""
import base64
import io
import logging
import os
import posixpath
import re
import urllib.error
import urllib.request
import zipfile

import streamlit as st

from components.cards import empty_state, file_type_chip, metric_card, section_header
from services import llm_service
from services import chat_service
from services.database_service import (
    LANGUAGE_MAPPING,
    get_all_files,
    get_chunk_count,
    get_file_content,
    get_file_count,
    get_language_breakdown,
    get_storage_label,
    insert_file_with_chunks,
)

logger = logging.getLogger("pages_dashboard")


# ══════════════════════════════════════════════════════════════════════
# GitHub Ingestion
# ══════════════════════════════════════════════════════════════════════
def parse_github_url(repo_url: str):
    url = (repo_url or "").strip()
    if not url:
        return None
    if url.endswith(".git"):
        url = url[:-4]

    if "git@github.com:" in url:
        path = url.split("git@github.com:")[-1]
    elif "github.com/" in url:
        path = url.split("github.com/")[-1]
    else:
        path = url

    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def check_repo_private(repo_url: str) -> bool:
    repo_path = parse_github_url(repo_url)
    if not repo_path:
        return False

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo_path}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        import json as _json

        with urllib.request.urlopen(req) as response:
            return bool(_json.loads(response.read().decode()).get("private", False))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            if e.headers.get("X-RateLimit-Remaining") == "0":
                return False
            try:
                if "rate limit" in e.read().decode("utf-8", errors="ignore").lower():
                    return False
            except Exception:
                pass
            return True
        if e.code in (401, 404):
            return True
        return False
    except Exception:
        return False


def download_and_filter_repo(repo_url: str, branch: str) -> list:
    repo_path = parse_github_url(repo_url)
    if not repo_path:
        raise ValueError("Invalid GitHub URL. Use https://github.com/owner/repository")

    def _fetch(ref):
        req = urllib.request.Request(
            f"https://github.com/{repo_path}/archive/refs/heads/{ref}.zip",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req) as response:
            return response.read()

    try:
        zip_data = _fetch(branch)
    except Exception:
        if branch == "main":
            zip_data = _fetch("master")
        else:
            raise

    allowed_exts = set(LANGUAGE_MAPPING) | {
        "yml", "toml", "sql", "sh", "bat", "ini", "cfg", "properties", "xml", "csv",
    }
    allowed_names = {"dockerfile", "license", "procfile", "gemfile", "makefile"}

    files_list = []
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            parts = name.split("/", 1)
            clean_name = parts[1] if len(parts) > 1 else name

            if (
                any(p.startswith(".") for p in clean_name.split("/"))
                or "node_modules/" in clean_name
                or "venv/" in clean_name
                or "__pycache__/" in clean_name
            ):
                continue

            ext = clean_name.rsplit(".", 1)[-1].lower() if "." in clean_name else ""
            base_name = clean_name.split("/")[-1].lower()
            if ext not in allowed_exts and base_name not in allowed_names:
                continue

            try:
                if z.getinfo(name).file_size > 300 * 1024:
                    continue
            except Exception:
                pass

            try:
                files_list.append({"path": clean_name, "content": z.read(name)})
            except Exception:
                pass
    return files_list


def clone_and_index(repo_url: str, branch: str):
    if not parse_github_url(repo_url):
        st.error("Invalid GitHub URL. Use https://github.com/owner/repository")
        return
    if check_repo_private(repo_url):
        st.error("This repository is private, so it can't be accessed.")
        return

    try:
        progress = st.progress(0)
        status = st.empty()
        files = download_and_filter_repo(repo_url, branch)
        if not files:
            st.warning("No indexable text files found in that repository.")
            progress.empty()
            return

        for i, f in enumerate(files):
            status.markdown(f"`Indexing {f['path']}`")
            insert_file_with_chunks(f)
            progress.progress((i + 1) / len(files))

        progress.empty()
        status.success(f"Indexed {len(files)} files from {repo_url}")

        readme = next(
            (
                f
                for f in files
                if f["path"].lower() in ("readme.md", "readme.txt")
                or f["path"].lower().endswith(("/readme.md", "/readme.txt"))
            ),
            None,
        )
        if readme:
            content = readme["content"]
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            st.session_state["last_repo_readme"] = content
            st.session_state["last_repo_explanation"] = None
        else:
            st.session_state["last_repo_readme"] = None
            st.session_state["last_repo_explanation"] = generate_project_explanation(files)

        st.session_state["last_repo_name"] = repo_url
        st.rerun()
    except Exception as ex:  # noqa: BLE001
        st.error(f"Failed to clone and index repository: {ex}")


# ══════════════════════════════════════════════════════════════════════
# LLM-backed project explanation
# ══════════════════════════════════════════════════════════════════════
def call_gemini(prompt: str, system_instruction: str = "") -> str:
    return llm_service.generate(system_instruction, prompt)


def generate_project_explanation(files: list) -> str:
    paths = [f["path"] for f in files]
    file_structure = "\n".join(paths[:100])
    if len(paths) > 100:
        file_structure += f"\n... and {len(paths) - 100} more files."

    key_files = ["app.py", "main.py", "index.js", "package.json",
                 "requirements.txt", "setup.py", "cargo.toml", "go.mod"]
    contexts = []
    for f in files:
        if len(contexts) >= 5:
            break
        if any(k in f["path"].lower() for k in key_files):
            content = f["content"]
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            contexts.append(f"File: {f['path']}\nContent:\n{content[:1500]}")

    prompt = f"""A user uploaded a GitHub repository that has no README.
Generate a clear explanation of the project covering:
1. **Purpose** — what is this project for?
2. **Structure** — outline the folder and file layout.
3. **Design** — architecture, patterns, and libraries used.

Use professional markdown formatting.

File structure:
```
{file_structure}
```

Key file contents:
{chr(10).join(contexts)}
"""
    try:
        return call_gemini(prompt, "You are an expert software architect.")
    except llm_service.LLMNotConfigured as e:
        return f"_{e}_"
    except Exception as e:  # noqa: BLE001
        return f"Failed to generate project explanation: {e}"


def ensure_readme_or_explanation():
    if st.session_state.get("last_repo_readme") or st.session_state.get(
        "last_repo_explanation"
    ):
        return

    files = get_all_files()
    if not files:
        return

    readme_id = next(
        (
            f["id"]
            for f in files
            if f["filename"].lower() in ("readme.md", "readme.txt", "readme.markdown", "readme")
            or f["filename"].lower().endswith(("/readme.md", "/readme.txt"))
        ),
        None,
    )

    st.session_state["last_repo_name"] = st.session_state.get(
        "last_repo_name", "Currently Indexed Workspace"
    )

    if readme_id:
        st.session_state["last_repo_readme"] = get_file_content(readme_id).get("content")
        st.session_state["last_repo_explanation"] = None
    else:
        st.session_state["last_repo_readme"] = None
        db_files = [
            {"path": f["filename"], "content": get_file_content(f["id"]).get("content", "")}
            for f in files[:50]
        ]
        st.session_state["last_repo_explanation"] = generate_project_explanation(db_files)


# ══════════════════════════════════════════════════════════════════════
# Dashboard Sections
# ══════════════════════════════════════════════════════════════════════
def render_overview():
    section_header("Overview", "Workspace status and indexed content at a glance.", level=2)

    files = get_all_files()
    if not files:
        empty_state("◔", "Nothing indexed yet",
                    "Head to Ingest Repository to analyze your first codebase.")
        return

    source_files = [f for f in files if f["file_type"] == "source_code"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("☰", "Files indexed", get_file_count(), tone="accent")
    with c2:
        metric_card("◆", "Source files", len(source_files), tone="low")
    with c3:
        metric_card("⬡", "Chunks embedded", get_chunk_count(), tone="info")
    with c4:
        metric_card("▤", "Content size", get_storage_label(), tone="success")

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    if not llm_service.embeddings_available():
        st.info(
            "No Gemini key found, so chunks are stored without embeddings and search "
            "falls back to keyword matching. Set `GEMINI_API_KEY` in your environment to "
            "enable semantic search. (Your chat provider is unaffected.)"
        )

    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="dp-overline">Languages</div>', unsafe_allow_html=True)
        langs = get_language_breakdown()
        if langs:
            for lang, count in langs.items():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:6px 0;border-bottom:1px solid var(--border);">'
                    f'<span style="color:var(--text-primary);font-size:0.875rem">{lang}</span>'
                    f'<span style="color:var(--text-muted);font-size:0.875rem">{count}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
    with right:
        st.markdown('<div class="dp-overline">Repository</div>', unsafe_allow_html=True)
        repo = st.session_state.get("last_repo_name", "—")
        st.markdown(
            f'<div style="color:var(--text-primary);font-size:0.9rem;padding:6px 0">{repo}</div>',
            unsafe_allow_html=True,
        )


SAMPLE_REPOS = [
    ("Vulnerable Flask App", "https://github.com/we45/Vulnerable-Flask-App", "master",
     "Python · scores F"),
    ("Damn Vulnerable Web App", "https://github.com/anxolerd/dvpwa", "master",
     "Python · planted bugs"),
    ("Spoon-Knife", "https://github.com/octocat/Spoon-Knife", "main",
     "HTML & CSS"),
]


def render_ingestion_section():
    section_header("Ingest Repository",
                   "Download a public GitHub repository and index it for analysis.", level=2)

    st.session_state.setdefault("ingest_url", "")
    st.session_state.setdefault("ingest_branch", "main")

    st.markdown('<div class="dp-overline">Try a sample repository</div>',
                unsafe_allow_html=True)
    cols = st.columns(len(SAMPLE_REPOS))
    for col, (name, url, branch, note) in zip(cols, SAMPLE_REPOS):
        with col:
            if st.button(name, key=f"sample_{name}", use_container_width=True):
                st.session_state["ingest_url"] = url
                st.session_state["ingest_branch"] = branch
                st.rerun()
            st.caption(note)

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    repo_url = st.text_input("GitHub URL", key="ingest_url",
                             placeholder="https://github.com/owner/repo")
    branch = st.text_input("Branch", key="ingest_branch")

    col, _ = st.columns([1, 2])
    with col:
        if st.button("Analyze Repository", type="primary", use_container_width=True):
            if repo_url:
                clone_and_index(repo_url, branch)
            else:
                st.error("Enter a repository URL first.")

    with st.expander("Limitations & technical notes"):
        st.markdown(
            """
* **Private repositories** are not accessible — no GitHub token is configured.
* **Rate limits** apply to unauthenticated GitHub API and ZIP requests.
* **Large repositories** may hit free-tier memory limits or time out while embedding.
* **Filtered out:** binaries, images, `node_modules/`, `venv/`, dotfiles, and files over 300&nbsp;KB.
"""
        )


def render_project_overview():
    section_header("Project Overview", "README, or an AI-generated explanation if none exists.", level=2)

    ensure_readme_or_explanation()
    repo = st.session_state.get("last_repo_name")
    if not repo:
        empty_state("◇", "No repository analyzed",
                    "Ingest a repository to see its overview here.")
        return

    st.caption(f"Showing analysis for {repo}")
    readme = st.session_state.get("last_repo_readme")
    explanation = st.session_state.get("last_repo_explanation")

    if readme:
        st.success("README detected in repository")
        st.markdown("---")
        st.markdown(readme)
    elif explanation:
        st.warning("No README found — showing an AI-generated explanation")
        st.markdown("---")
        st.markdown(explanation)
    else:
        empty_state("◇", "Nothing to show", "No README or explanation available.")


# ══════════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════════
def render_unified_dashboard():
    section_header("DevPulse Architect", "Codebase Ingestion & AI Chat Assistant", level=1)

    # 1. Ingestion & Overview side-by-side
    col_left, col_right = st.columns([1.1, 0.9])
    with col_left:
        render_ingestion_section()
    with col_right:
        render_overview()

    st.markdown("---")

    files = get_all_files()
    if files:
        # 2. Repo Overview (README / AI Explanation)
        with st.expander("◇  Repository Overview & Architecture", expanded=True):
            render_project_overview()
    else:
        empty_state("💬", "Workspace is empty", "Ingest a repository above to enable codebase overview and AI chat.")

