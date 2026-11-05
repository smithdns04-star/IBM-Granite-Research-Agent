"""
report_generator.py – 14-section academic research report generator.

Uses IBM Granite via Ollama to produce a structured academic report
based on information retrieved from Wikipedia, OpenAlex and Crossref.
"""

import logging

from src.ollama_client import generate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_REPORT_PROMPT = """You are an expert academic research writer powered by IBM Granite.

Research Topic: {topic}

Background Information Retrieved from Research Sources:
{research_data}

Write a complete, professional academic research report on the above topic.
Use ONLY the background information provided — do not invent statistics, dates or fabricate references.

Structure the report with these EXACT section headings (use ## for each):

## Title
## Abstract
## Introduction
## Problem Statement
## Research Objectives
## Literature Review
## Methodology
## Data Analysis
## Key Findings
## Applications
## Challenges and Limitations
## Future Scope
## Conclusion
## References

Guidelines:
- Write in clear, formal academic English.
- Literature Review must discuss the sources provided by title and year where available.
- References section must list only the sources provided, formatted as numbered citations.
- Data Analysis should interpret and contextualise findings from the sources.
- Do not add any preamble or closing remarks outside the section headings.
- Keep each section substantive (2–4 paragraphs for major sections).
- Report length: {length_instruction}
"""

_LENGTH_MAP = {
    "Short (500–800 words)": "write a concise report of approximately 500–800 words total",
    "Standard (1000–1500 words)": "write a standard report of approximately 1000–1500 words total",
    "Detailed (2000–2500 words)": "write a detailed report of approximately 2000–2500 words total",
    "Comprehensive (3000+ words)": "write a comprehensive report of 3000 or more words total",
}


def _build_research_data(information: list) -> str:
    """Format the list of source dicts into a text block for the prompt."""
    parts = []
    for i, item in enumerate(information, 1):
        src_type = item.get("source_type", "source").upper()
        authors = item.get("authors", "")
        year = item.get("year", "")
        journal = item.get("journal", "")
        url = item.get("url", "")

        header_parts = [f"[{i}] [{src_type}] {item['title']}"]
        if authors:
            header_parts.append(f"Authors: {authors}")
        if year:
            header_parts.append(f"Year: {year}")
        if journal:
            header_parts.append(f"Published in: {journal}")
        if url:
            header_parts.append(f"URL: {url}")

        parts.append("\n".join(header_parts) + "\n" + item.get("summary", ""))

    return "\n\n---\n\n".join(parts)


def generate_report(
    topic: str,
    information: list,
    length: str = "Standard (1000–1500 words)",
) -> str:
    """
    Generate the full 14-section research report using IBM Granite.

    Parameters
    ----------
    topic       : str  – research topic.
    information : list – source dicts from information_search.
    length      : str  – one of the keys in _LENGTH_MAP.

    Returns
    -------
    str – formatted report markdown.
    """
    research_data = _build_research_data(information)
    length_instruction = _LENGTH_MAP.get(length, _LENGTH_MAP["Standard (1000–1500 words)"])

    prompt = _REPORT_PROMPT.format(
        topic=topic,
        research_data=research_data,
        length_instruction=length_instruction,
    )

    logger.info("Requesting Granite report for: %s (length: %s)", topic, length)
    report = generate(prompt, timeout=360)
    logger.info("Report generated (%d chars)", len(report))
    return report
