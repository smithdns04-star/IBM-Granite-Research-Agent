"""
information_search.py – Multi-source research information retrieval.

Sources
-------
1. Wikipedia  – general background (free, no key)
2. OpenAlex   – academic papers and publications (free, no key)
3. Crossref   – publication metadata with DOIs (free, no key)

All sources are free public APIs. No API keys are required.
Internet connectivity is required. Failures per source are handled
gracefully – the module always returns whatever it could retrieve.
"""

import logging
import os
import time

import requests
import wikipedia
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# OpenAlex politely requests an email for higher rate limits (optional)
_OPENALEX_EMAIL: str = os.getenv("OPENALEX_EMAIL", "")
_REQUEST_TIMEOUT: int = 15  # seconds per HTTP request


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------

def search_wikipedia(topic: str, max_results: int = 5) -> list[dict]:
    """
    Fetch Wikipedia page summaries for *topic*.

    Returns
    -------
    list of dicts with keys: title, summary, url, source_type="wikipedia"
    """
    if not topic or not topic.strip():
        return []

    wikipedia.set_lang("en")
    results: list[dict] = []

    try:
        titles = wikipedia.search(topic, results=max_results)
    except Exception as exc:
        logger.warning("Wikipedia search failed: %s", exc)
        return []

    for title in titles:
        try:
            page = wikipedia.page(title, auto_suggest=False, redirect=True)
            results.append({
                "title": page.title,
                "summary": page.summary[:3000],
                "url": page.url,
                "source_type": "wikipedia",
                "authors": "",
                "year": "",
                "journal": "",
            })
        except wikipedia.exceptions.DisambiguationError as exc:
            try:
                page = wikipedia.page(exc.options[0], auto_suggest=False, redirect=True)
                results.append({
                    "title": page.title,
                    "summary": page.summary[:3000],
                    "url": page.url,
                    "source_type": "wikipedia",
                    "authors": "",
                    "year": "",
                    "journal": "",
                })
            except Exception:
                continue
        except Exception as exc:
            logger.debug("Wikipedia skip '%s': %s", title, exc)
            continue

    logger.info("Wikipedia: retrieved %d pages for '%s'", len(results), topic)
    return results


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

_OPENALEX_SEARCH_URL = "https://api.openalex.org/works"


def search_openalex(topic: str, max_results: int = 5) -> list[dict]:
    """
    Search OpenAlex for academic works related to *topic*.

    Returns
    -------
    list of dicts with keys:
        title, summary, url, source_type="openalex",
        authors, year, journal, doi
    """
    results: list[dict] = []

    params: dict = {
        "search": topic,
        "per-page": max_results,
        "select": "title,abstract_inverted_index,authorships,publication_year,primary_location,doi,open_access",
        "sort": "cited_by_count:desc",
    }
    if _OPENALEX_EMAIL:
        params["mailto"] = _OPENALEX_EMAIL

    try:
        resp = requests.get(
            _OPENALEX_SEARCH_URL, params=params, timeout=_REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("OpenAlex request timed out for '%s'", topic)
        return []
    except requests.exceptions.ConnectionError:
        logger.warning("OpenAlex: no internet connection")
        return []
    except Exception as exc:
        logger.warning("OpenAlex request failed: %s", exc)
        return []

    for work in data.get("results", []):
        title = work.get("title") or ""
        if not title:
            continue

        # Reconstruct abstract from inverted index
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index") or {})

        # Authors
        authorships = work.get("authorships", [])
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in authorships[:3]
            if a.get("author", {}).get("display_name")
        )

        year = str(work.get("publication_year") or "")

        # Journal / venue
        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        journal = source.get("display_name", "")

        doi = work.get("doi") or ""
        url = doi if doi.startswith("http") else (f"https://doi.org/{doi}" if doi else "")
        if not url:
            url = f"https://openalex.org/works?search={requests.utils.quote(title)}"

        oa = work.get("open_access") or {}
        oa_url = oa.get("oa_url") or url

        results.append({
            "title": title,
            "summary": abstract or f"Academic paper: {title}",
            "url": oa_url,
            "source_type": "openalex",
            "authors": authors,
            "year": year,
            "journal": journal,
            "doi": doi,
        })

    logger.info("OpenAlex: retrieved %d works for '%s'", len(results), topic)
    return results


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    try:
        max_pos = max(p for positions in inverted_index.values() for p in positions)
        words = [""] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(w for w in words if w)[:2000]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------

_CROSSREF_URL = "https://api.crossref.org/works"


def search_crossref(topic: str, max_results: int = 5) -> list[dict]:
    """
    Search Crossref for publications related to *topic*.

    Returns
    -------
    list of dicts with keys:
        title, summary, url, source_type="crossref",
        authors, year, journal, doi
    """
    results: list[dict] = []

    params: dict = {
        "query": topic,
        "rows": max_results,
        "select": "title,author,published,container-title,DOI,abstract,URL",
        "sort": "relevance",
        "order": "desc",
    }

    try:
        resp = requests.get(
            _CROSSREF_URL, params=params, timeout=_REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("Crossref request timed out for '%s'", topic)
        return []
    except requests.exceptions.ConnectionError:
        logger.warning("Crossref: no internet connection")
        return []
    except Exception as exc:
        logger.warning("Crossref request failed: %s", exc)
        return []

    for item in data.get("message", {}).get("items", []):
        title_list = item.get("title") or []
        title = title_list[0] if title_list else ""
        if not title:
            continue

        authors_list = item.get("author") or []
        authors = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in authors_list[:3]
            if a.get("family")
        )

        pub = item.get("published") or {}
        date_parts = pub.get("date-parts") or [[""]]
        year = str(date_parts[0][0]) if date_parts[0] else ""

        container = item.get("container-title") or []
        journal = container[0] if container else ""

        doi = item.get("DOI") or ""
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")

        abstract_raw = item.get("abstract") or ""
        # Crossref abstracts sometimes have JATS XML tags
        import re
        abstract = re.sub(r"<[^>]+>", " ", abstract_raw).strip()[:2000]
        summary = abstract or f"Publication: {title} ({year})"

        results.append({
            "title": title,
            "summary": summary,
            "url": url,
            "source_type": "crossref",
            "authors": authors,
            "year": year,
            "journal": journal,
            "doi": doi,
        })

    logger.info("Crossref: retrieved %d works for '%s'", len(results), topic)
    return results


# ---------------------------------------------------------------------------
# Combined search (all sources)
# ---------------------------------------------------------------------------

def search_all_sources(
    topic: str,
    max_wiki: int = 4,
    max_academic: int = 5,
) -> dict:
    """
    Search all three sources and return combined results.

    Returns
    -------
    dict with keys:
        wikipedia  : list[dict]
        openalex   : list[dict]
        crossref   : list[dict]
        all        : list[dict]   (combined, deduplicated)
        sources    : list[str]    (all URLs)
        errors     : list[str]
    """
    if not topic or not topic.strip():
        raise ValueError("Please enter a research topic.")

    errors: list[str] = []

    wiki = search_wikipedia(topic, max_results=max_wiki)
    if not wiki:
        errors.append("Wikipedia: no results retrieved (check internet connection).")

    oa = search_openalex(topic, max_results=max_academic)
    if not oa:
        errors.append("OpenAlex: no results retrieved (check internet connection).")

    cr = search_crossref(topic, max_results=max_academic)
    if not cr:
        errors.append("Crossref: no results retrieved (check internet connection).")

    combined = wiki + oa + cr

    if not combined:
        raise RuntimeError(
            f"No research information found for '{topic}' from any source. "
            "Check your internet connection."
        )

    # Deduplicate by URL (keep first occurrence)
    seen_urls: set = set()
    deduped: list[dict] = []
    for item in combined:
        url = item.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            deduped.append(item)

    all_urls = [item["url"] for item in deduped if item.get("url")]

    return {
        "wikipedia": wiki,
        "openalex": oa,
        "crossref": cr,
        "all": deduped,
        "sources": all_urls,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Legacy compatibility – used by research_agent.py
# ---------------------------------------------------------------------------

def search_information(topic: str, max_results: int = 5) -> tuple:
    """
    Backward-compatible wrapper.

    Returns
    -------
    (information_list, sources_list)
    """
    result = search_all_sources(topic, max_wiki=max_results, max_academic=max_results)
    return result["all"], result["sources"]
