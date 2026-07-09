# pages/security_audit.py
"""Security Audit section: run the scan, browse findings, export the report."""
import logging

import streamlit as st

from components.cards import empty_state, metric_card, section_header, severity_badge
from services import audit_service, llm_service, report_service
from services.database_service import get_all_files, get_latest_audit

logger = logging.getLogger("pages_security_audit")

SEVERITIES = ["critical", "high", "medium", "low", "info"]
GRADE_TONE = {"A": "success", "B": "success", "C": "medium", "D": "high", "F": "critical"}


def _run_audit(repo_name: str, use_llm: bool):
    progress = st.progress(0.0)
    status = st.empty()

    def cb(done, total, label):
        progress.progress(done / max(total, 1))
        status.caption(f"Analyzing {label}  ({done}/{total})")

    try:
        audit = audit_service.run_full_audit(repo_name, use_llm=use_llm, progress_cb=cb)
    finally:
        progress.empty()
        status.empty()

    st.session_state["last_audit"] = audit
    st.session_state.pop("audit_pdf", None)  # invalidate any cached PDF
    return audit


def _render_summary(audit):
    summary = audit["summary"]
    counts = summary["counts"]

    cols = st.columns(6)
    icons = {"critical": "▲", "high": "▲", "medium": "●", "low": "●", "info": "○"}
    for col, sev in zip(cols, SEVERITIES):
        with col:
            metric_card(icons[sev], sev, counts.get(sev, 0), tone=sev)
    with cols[5]:
        metric_card("★", "Score", f"{summary['score']}",
                    tone=GRADE_TONE.get(summary["grade"], "info"),
                    delta=f"Grade {summary['grade']}")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    if not audit.get("llm_used"):
        st.info(
            "**Static heuristics only.** AI deep analysis was skipped because no API "
            "key is configured. Add one in Settings for a much richer report."
        )


def _render_findings(audit):
    findings = audit["findings"]
    if not findings:
        empty_state("✓", "No issues detected",
                    "Neither the static rules nor the AI pass found a security problem.")
        return

    st.markdown('<div class="dp-overline">Findings</div>', unsafe_allow_html=True)

    present = [s for s in SEVERITIES if any(f["severity"] == s for f in findings)]
    c1, c2 = st.columns([2, 3])
    with c1:
        chosen = st.multiselect("Severity", present, default=present,
                                label_visibility="collapsed")
    with c2:
        needle = st.text_input("Filter", placeholder="Filter by title, file, or CWE…",
                               label_visibility="collapsed")

    shown = [f for f in findings if f["severity"] in chosen]
    if needle:
        n = needle.lower()
        shown = [
            f for f in shown
            if n in f["title"].lower() or n in f["file"].lower() or n in f["cwe"].lower()
        ]

    if not shown:
        st.caption("No findings match those filters.")
        return

    st.caption(f"Showing {len(shown)} of {len(findings)} findings")

    for f in shown:
        loc = f["file"] + (f":{f['line']}" if f["line"] else "")
        with st.expander(f"{f['severity'].upper()}  ·  {f['title']}  —  {loc}"):
            st.markdown(
                f"{severity_badge(f['severity'])} &nbsp; "
                f"<span class='dp-chip'>{f['category']}</span> &nbsp; "
                f"<span class='dp-chip'>{f['cwe']}</span> &nbsp; "
                f"<span class='dp-chip'>via {f['source']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Location:** `{loc}`")
            if f["source"] == "llm" and f["line"]:
                st.caption("Line number is AI-reported and approximate.")
            if f.get("description"):
                st.markdown(f["description"])
            if f.get("evidence"):
                st.code(f["evidence"])
            if f.get("remediation"):
                st.markdown(f"**Remediation:** {f['remediation']}")


def _render_exports(audit):
    st.markdown('<div class="dp-overline">Export</div>', unsafe_allow_html=True)
    repo_slug = (audit["repo_name"] or "report").replace("/", "_").replace(":", "")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download Markdown",
            report_service.build_markdown_report(audit),
            file_name=f"security_audit_{repo_slug}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        # Streamlit reruns on every interaction; rebuilding the PDF each time is wasteful.
        cache_key = ("audit_pdf", audit.get("id"))
        if st.session_state.get("audit_pdf_key") != cache_key:
            try:
                st.session_state["audit_pdf"] = report_service.build_pdf_report(audit)
                st.session_state["audit_pdf_key"] = cache_key
            except ImportError:
                st.session_state["audit_pdf"] = None
            except Exception as e:  # noqa: BLE001
                logger.warning("PDF build failed: %s", e)
                st.session_state["audit_pdf"] = None

        pdf = st.session_state.get("audit_pdf")
        if pdf:
            st.download_button(
                "Download PDF",
                pdf,
                file_name=f"security_audit_{repo_slug}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True)
            st.caption("Install `fpdf2` to enable PDF export.")


def render_security_audit():
    section_header("Security Audit",
                   "Static rules plus AI analysis over every indexed source file.")

    source_files = [
        f for f in get_all_files() if f.get("file_type") == "source_code"
    ]
    if not source_files:
        empty_state("⛨", "No source code indexed",
                    "Ingest a repository before running an audit.")
        return

    has_key = llm_service.resolve_key()[0] is not None
    if not has_key:
        st.info(
            "No API key configured, so only the free static rules will run. "
            "Add a key in Settings to enable AI deep analysis."
        )

    c1, c2 = st.columns([1, 3])
    with c1:
        run = st.button("Run Security Audit", type="primary", use_container_width=True)
    with c2:
        st.caption(
            f"{len(source_files)} source file(s) will be scanned by the static rules"
            + (f"; up to {audit_service.MAX_LLM_FILES} will also get AI analysis."
               if has_key else ".")
        )

    if run:
        repo = st.session_state.get("last_repo_name", "Indexed Workspace")
        try:
            _run_audit(repo, use_llm=has_key)
        except Exception as e:  # noqa: BLE001
            st.error(f"Audit failed: {e}")
            return

    audit = st.session_state.get("last_audit") or get_latest_audit()
    if not audit:
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        empty_state("⛨", "No audit yet", "Run an audit to see findings here.")
        return

    # A DB-loaded audit stores llm_used implicitly; default to True for old rows.
    audit.setdefault("llm_used", True)

    st.markdown("---")
    _render_summary(audit)
    _render_exports(audit)

    skipped = audit.get("files_skipped") or []
    if skipped:
        with st.expander(f"Coverage notes — {len(skipped)} item(s) not fully analyzed"):
            for s in skipped:
                st.markdown(f"- `{s['file']}` — {s['reason']}")

    st.markdown("---")
    _render_findings(audit)
