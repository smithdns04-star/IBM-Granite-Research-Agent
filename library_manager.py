"""
Research library manager.

Persists research reports to disk (JSON index + individual .txt files)
and provides search and delete operations.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage paths – relative to the project root
# ---------------------------------------------------------------------------
_PROJECT_DIR = Path(__file__).resolve().parent.parent
_LIBRARY_DIR = _PROJECT_DIR / "library"
_INDEX_FILE = _LIBRARY_DIR / "index.json"


def _ensure_dirs() -> None:
    _LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list:
    """Return the list of saved report metadata dicts."""
    _ensure_dirs()
    if not _INDEX_FILE.exists():
        return []
    try:
        with open(_INDEX_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Could not load library index: %s", exc)
        return []


def _save_index(index: list) -> None:
    _ensure_dirs()
    with open(_INDEX_FILE, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)


def _safe_filename(topic: str) -> str:
    """Convert a topic string into a safe file name prefix."""
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", topic)
    return safe[:60]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_report(topic: str, report: str, sources: list) -> str:
    """
    Save a research report to the library.

    Returns
    -------
    str – the absolute path to the saved report file.
    """
    _ensure_dirs()
    index = _load_index()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_filename(topic)}_{timestamp}.txt"
    report_path = _LIBRARY_DIR / filename

    full_content = (
        f"IBM GRANITE RESEARCH AGENT\n"
        f"Research Topic: {topic}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'='*60}\n\n"
        f"{report}\n\n"
        f"{'='*60}\n"
        f"SOURCES CONSULTED\n"
        + "\n".join(f"- {s}" for s in sources)
    )

    report_path.write_text(full_content, encoding="utf-8")

    index.append(
        {
            "id": timestamp,
            "topic": topic,
            "filename": filename,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sources_count": len(sources),
        }
    )
    _save_index(index)

    logger.info("Report saved: %s", report_path)
    return str(report_path)


def list_reports() -> list:
    """
    Return all saved report metadata sorted newest-first.

    Each item is a dict with keys: id, topic, filename, created, sources_count.
    """
    index = _load_index()
    return sorted(index, key=lambda r: r.get("created", ""), reverse=True)


def get_report(filename: str) -> str:
    """
    Read and return the text content of a saved report.

    Raises
    ------
    FileNotFoundError – if the file does not exist.
    """
    path = _LIBRARY_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {filename}")
    return path.read_text(encoding="utf-8")


def delete_report(filename: str) -> None:
    """
    Delete a report file and remove it from the index.

    Raises
    ------
    FileNotFoundError – if the file does not exist.
    """
    path = _LIBRARY_DIR / filename
    if path.exists():
        path.unlink()

    index = _load_index()
    index = [r for r in index if r.get("filename") != filename]
    _save_index(index)
    logger.info("Report deleted: %s", filename)


def search_reports(query: str) -> list:
    """
    Return reports whose topic contains *query* (case-insensitive).
    """
    q = query.strip().lower()
    if not q:
        return list_reports()
    return [r for r in list_reports() if q in r.get("topic", "").lower()]
