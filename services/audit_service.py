# services/audit_service.py
"""Two-pass security audit.

Pass A: pure-Python regex heuristics over *every* source file. Free, fast, and
        guarantees no file is completely unscanned even when the LLM pass is capped.
Pass B: an LLM deep-analysis pass over a prioritized subset, seeded with the
        heuristic hits for that file.

No Streamlit imports and no import from pages.* (dashboard imports services, so the
reverse would be a cycle).
"""
import hashlib
import json
import logging
import re
from collections import Counter

from services import llm_service
from services.database_service import (
    get_all_files,
    get_file_content,
    save_audit,
    search_chunks_vector,
)

logger = logging.getLogger("audit_service")

MAX_LLM_FILES = 40
MAX_FILE_BYTES = 40 * 1024

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_WEIGHTS = {"critical": 20, "high": 10, "medium": 4, "low": 1, "info": 0}

PY = ("python",)
JS = ("javascript", "typescript")
ANY = None  # applies to every language

# A real SQL statement, not just the English word "delete"/"insert". Without the
# structural anchor, `logger.error(f"delete failed: {e}")` matches.
_SQL_STMT = (
    r"(?:select\b[^\"']*\bfrom\b|insert\s+into\b|update\b[^\"']*\bset\b|delete\s+from\b)"
)


# ── Pass A: static heuristics ────────────────────────────────────────
RULES = [
    dict(id="aws-access-key", title="AWS access key ID committed in source",
         severity="critical", category="Secrets", cwe="CWE-798",
         pattern=r"AKIA[0-9A-Z]{16}", langs=ANY),
    dict(id="private-key-block", title="Private key material committed in source",
         severity="critical", category="Secrets", cwe="CWE-798",
         pattern=r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", langs=ANY),
    # \w* on both sides so SECRET_KEY / my_api_key / AUTH_TOKEN all match, not just
    # a bare `secret =`. Requires a quoted literal, so os.getenv("API_KEY") is ignored.
    dict(id="hardcoded-secret", title="Hardcoded credential or API key",
         severity="high", category="Secrets", cwe="CWE-798",
         pattern=r"(?i)\b\w*(?:api[_-]?key|secret|password|passwd|token)\w*\s*[:=]\s*"
                 r"['\"][A-Za-z0-9_\-/+!@#$%^&*.]{10,}['\"]",
         langs=ANY),
    dict(id="eval-exec", title="Dynamic code execution via eval/exec",
         severity="high", category="Injection", cwe="CWE-95",
         pattern=r"\b(?:eval|exec)\s*\(", langs=ANY),
    dict(id="os-system", title="Shell command execution via os.system",
         severity="high", category="Command Injection", cwe="CWE-78",
         pattern=r"\bos\.system\s*\(", langs=PY),
    dict(id="shell-true", title="subprocess called with shell=True",
         severity="high", category="Command Injection", cwe="CWE-78",
         pattern=r"subprocess\.(?:run|Popen|call|check_output)[^\n]*shell\s*=\s*True",
         langs=PY),
    dict(id="node-child-exec", title="child_process.exec with shell semantics",
         severity="high", category="Command Injection", cwe="CWE-78",
         pattern=r"child_process\.exec\s*\(", langs=JS),
    # Two shapes: an f-string containing a SQL statement with a {} placeholder, or an
    # execute() whose query is assembled with % / + concatenation.
    dict(id="sql-fstring", title="SQL query built by string interpolation",
         severity="high", category="SQL Injection", cwe="CWE-89",
         pattern=rf"(?i)\bf[\"'][^\"']*{_SQL_STMT}.*?\{{"
                 rf"|(?:cursor\.)?execute\s*\(\s*[\"'][^\"']*{_SQL_STMT}[^\"']*[\"']\s*(?:%|\+)",
         langs=ANY),
    dict(id="insecure-deser", title="Insecure deserialization",
         severity="high", category="Deserialization", cwe="CWE-502",
         pattern=r"\bpickle\.loads?\s*\(|\byaml\.load\s*\((?![^)]*SafeLoader)", langs=PY),
    dict(id="weak-hash", title="Weak hash algorithm (MD5/SHA-1)",
         severity="medium", category="Cryptography", cwe="CWE-327",
         pattern=r"hashlib\.(?:md5|sha1)\s*\(|createHash\s*\(\s*['\"](?:md5|sha1)['\"]",
         langs=ANY),
    dict(id="tls-verify-off", title="TLS certificate verification disabled",
         severity="medium", category="Transport Security", cwe="CWE-295",
         pattern=r"verify\s*=\s*False|_create_unverified_context|rejectUnauthorized\s*:\s*false",
         langs=ANY),
    dict(id="debug-on", title="Debug mode enabled",
         severity="medium", category="Configuration", cwe="CWE-489",
         pattern=r"(?i)\bDEBUG\s*=\s*True\b|debug\s*:\s*true", langs=ANY),
    dict(id="xss-sink", title="Unsanitized DOM sink (possible XSS)",
         severity="medium", category="Cross-Site Scripting", cwe="CWE-79",
         pattern=r"\.innerHTML\s*=|dangerouslySetInnerHTML|document\.write\s*\(", langs=JS),
    dict(id="cors-wildcard", title="Permissive CORS wildcard origin",
         severity="low", category="Configuration", cwe="CWE-942",
         pattern=r"Access-Control-Allow-Origin[\"'\s:]+\*", langs=ANY),
]

_MULTILINE_RULES = {"private-key-block"}
_COMPILED = [(r, re.compile(r["pattern"])) for r in RULES]


def _finding_id(file, line, cwe):
    # sha256, not sha1: this is a dedup key, not a security hash, but using a weak
    # digest here would make the scanner flag its own source.
    return hashlib.sha256(f"{file}:{line}:{cwe}".encode()).hexdigest()[:10]


def _make_finding(rule, file, line, evidence, source="heuristic", **extra):
    return {
        "id": _finding_id(file, line, rule["cwe"]),
        "title": rule["title"],
        "severity": rule["severity"],
        "file": file,
        "line": line,
        "category": rule["category"],
        "cwe": rule["cwe"],
        "description": extra.get("description", ""),
        "evidence": (evidence or "").strip()[:300],
        "remediation": extra.get("remediation", ""),
        "confidence": extra.get("confidence", "high"),
        "source": source,
    }


def scan_file(path: str, content: str, language: str = None) -> list:
    """Run every applicable heuristic rule over one file."""
    findings = []
    lines = content.splitlines()
    for rule, regex in _COMPILED:
        if rule["langs"] is not None and language not in rule["langs"]:
            continue
        if rule["id"] in _MULTILINE_RULES:
            m = regex.search(content)
            if m:
                line_no = content[: m.start()].count("\n") + 1
                findings.append(_make_finding(rule, path, line_no, m.group(0)))
            continue
        for line_no, line in enumerate(lines, 1):
            m = regex.search(line)
            if m:
                findings.append(_make_finding(rule, path, line_no, line))
    return findings


def run_heuristic_scan(files: list) -> list:
    """files: [{path, content, language}] -> findings list."""
    out = []
    for f in files:
        try:
            out.extend(scan_file(f["path"], f["content"], f.get("language")))
        except Exception as e:  # noqa: BLE001
            logger.warning("Heuristic scan failed for %s: %s", f["path"], e)
    return out


# ── Pass B: LLM deep analysis ────────────────────────────────────────
_AUDIT_SYSTEM = """You are a senior application security auditor.
Analyse the provided source file for real, exploitable security issues \
(OWASP Top 10 / CWE).

Return ONLY a JSON array. Each element must be an object with these keys:
  title        short issue name
  severity     one of: critical, high, medium, low, info
  line         integer line number (best effort)
  category     e.g. "SQL Injection"
  cwe          e.g. "CWE-89"
  description  why it is a problem
  evidence     the offending code snippet
  remediation  a concrete fix, with corrected code where useful
  confidence   high, medium, or low

If the file contains no security issues, return exactly: []
Do not invent issues. Do not include commentary outside the JSON array."""


def _strip_json_fence(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


def _parse_findings_json(raw: str):
    """Parse an LLM JSON array, salvaging the first [...] block if needed."""
    cleaned = _strip_json_fence(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\[.*\]", cleaned, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def audit_file_with_llm(path: str, content: str, heuristic_hits: list) -> list:
    """Ask the LLM to confirm/expand on one file. Raises on parse/API failure."""
    hint = ""
    if heuristic_hits:
        listed = "\n".join(
            f"- line {h['line']}: {h['title']} ({h['cwe']})" for h in heuristic_hits
        )
        hint = f"\nA static scanner already flagged:\n{listed}\nConfirm or expand on these.\n"

    prompt = f"File: {path}{hint}\n\n```\n{content}\n```"
    raw = llm_service.generate(_AUDIT_SYSTEM, prompt)
    parsed = _parse_findings_json(raw)

    out = []
    for item in parsed:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        sev = str(item.get("severity", "info")).lower()
        if sev not in SEVERITY_WEIGHTS:
            sev = "info"
        try:
            line = int(item.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        cwe = item.get("cwe", "")
        out.append({
            "id": _finding_id(path, line, cwe),
            "title": item["title"],
            "severity": sev,
            "file": path,
            "line": line,
            "category": item.get("category", "Other"),
            "cwe": cwe,
            "description": item.get("description", ""),
            "evidence": str(item.get("evidence", ""))[:300],
            "remediation": item.get("remediation", ""),
            "confidence": str(item.get("confidence", "medium")).lower(),
            "source": "llm",
        })
    return out


# ── Merge, score, orchestrate ────────────────────────────────────────
def merge_findings(heuristic: list, llm: list) -> list:
    """De-dup on (file, line, cwe); prefer the heuristic line number."""
    merged = {}
    for f in heuristic:
        merged[(f["file"], f["line"], f["cwe"])] = f
    for f in llm:
        key = (f["file"], f["line"], f["cwe"])
        if key in merged:
            # Keep the heuristic's line, take the LLM's richer prose.
            base = merged[key]
            base["description"] = f["description"] or base["description"]
            base["remediation"] = f["remediation"] or base["remediation"]
            base["source"] = "both"
        else:
            merged[key] = f
    return sorted(
        merged.values(),
        key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["file"], f["line"]),
    )


def aggregate(findings: list) -> dict:
    counts = Counter(f["severity"] for f in findings)
    penalty = sum(SEVERITY_WEIGHTS[s] * n for s, n in counts.items())
    score = max(0, 100 - penalty)
    grade = (
        "A" if score >= 90 else
        "B" if score >= 80 else
        "C" if score >= 70 else
        "D" if score >= 60 else "F"
    )
    return {
        "counts": {s: counts.get(s, 0) for s in SEVERITY_WEIGHTS},
        "score": score,
        "grade": grade,
        "total": len(findings),
    }


def _prioritize(source_files: list, heuristic: list) -> tuple:
    """Return (selected, skipped) honouring MAX_LLM_FILES."""
    flagged = {f["file"] for f in heuristic}

    risky = set()
    try:
        matches = search_chunks_vector(
            "authentication password secret token sql query subprocess exec deserialize",
            limit=15,
            file_types=["source_code"],
        )
        risky = {m["filename"] for m in matches}
    except Exception as e:  # noqa: BLE001
        logger.warning("Vector focus unavailable, falling back to size order: %s", e)

    def rank(f):
        return (
            0 if f["path"] in flagged else 1 if f["path"] in risky else 2,
            len(f["content"]),
        )

    ordered = sorted(source_files, key=rank)
    selected, skipped = ordered[:MAX_LLM_FILES], ordered[MAX_LLM_FILES:]
    skipped_log = [
        {"file": f["path"], "reason": f"over the {MAX_LLM_FILES}-file AI analysis cap"}
        for f in skipped
    ]
    return selected, skipped_log


def load_source_files() -> list:
    """Fetch every indexed source file with its content."""
    out = []
    for meta in get_all_files():
        if meta.get("file_type") != "source_code":
            continue
        row = get_file_content(meta["id"])
        out.append({
            "path": meta["filename"],
            "content": row.get("content") or "",
            "language": meta.get("language"),
        })
    return out


def run_full_audit(repo_name: str, use_llm: bool = True, progress_cb=None) -> dict:
    """Run both passes and persist. progress_cb(done, total, label) is optional."""
    source_files = load_source_files()
    if not source_files:
        raise ValueError("No source files indexed. Ingest a repository first.")

    heuristic = run_heuristic_scan(source_files)

    llm_findings, skipped = [], []
    if use_llm:
        selected, skipped = _prioritize(source_files, heuristic)
        by_file = {}
        for f in heuristic:
            by_file.setdefault(f["file"], []).append(f)

        for i, f in enumerate(selected, 1):
            if progress_cb:
                progress_cb(i, len(selected), f["path"])

            content = f["content"]
            if len(content.encode("utf-8", errors="ignore")) > MAX_FILE_BYTES:
                content = content[:MAX_FILE_BYTES] + "\n...[truncated]"
                skipped.append({"file": f["path"], "reason": "truncated to fit the context window"})

            try:
                llm_findings.extend(
                    audit_file_with_llm(f["path"], content, by_file.get(f["path"], []))
                )
            except json.JSONDecodeError:
                logger.warning("LLM returned unparseable JSON for %s", f["path"])
                skipped.append({"file": f["path"], "reason": "AI response was not valid JSON"})
            except Exception as e:  # noqa: BLE001 - one bad file must not abort the run
                logger.warning("LLM audit failed for %s: %s", f["path"], e)
                skipped.append({"file": f["path"], "reason": f"AI analysis failed: {e}"})
    else:
        skipped = [{"file": "(all files)", "reason": "AI deep analysis skipped — no API key"}]

    findings = merge_findings(heuristic, llm_findings)
    summary = aggregate(findings)

    audit = {
        "repo_name": repo_name,
        "summary": summary,
        "findings": findings,
        "score": summary["score"],
        "grade": summary["grade"],
        "files_scanned": len(source_files),
        "files_skipped": skipped,
        "llm_used": use_llm,
    }

    audit["id"] = save_audit(
        repo_name,
        json.dumps(summary),
        json.dumps(findings),
        summary["score"],
        summary["grade"],
        len(source_files),
        json.dumps(skipped),
    )
    return audit
