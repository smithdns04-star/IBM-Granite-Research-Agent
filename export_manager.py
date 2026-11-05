"""
Export manager module.

Generates downloadable TXT and PDF versions of research reports.
PDF generation uses fpdf2 (pure-Python, no external tools required).

Compatible with fpdf2 >= 2.7 (including v2.9 which requires explicit
new_x/new_y on multi_cell calls).
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Shorthand for fpdf2 v2.9+ multi_cell cursor reset
_MC_KWARGS = {"new_x": "LMARGIN", "new_y": "NEXT"}


def _latin1_safe(text: str) -> str:
    """Encode text to Latin-1 safe subset (built-in Helvetica font requirement)."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# TXT export
# ---------------------------------------------------------------------------

def export_txt(topic: str, report: str, sources: list) -> bytes:
    """
    Return the report as UTF-8 encoded plain text bytes.

    Parameters
    ----------
    topic   : research topic string.
    report  : full report markdown/text.
    sources : list of source URLs.
    """
    lines = [
        "=" * 70,
        "IBM GRANITE RESEARCH AGENT",
        "=" * 70,
        f"Research Topic : {topic}",
        f"Generated      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
        report,
        "",
        "=" * 70,
        "SOURCES CONSULTED",
        "=" * 70,
    ]
    for src in sources:
        lines.append(f"  - {src}")

    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def export_pdf(topic: str, report: str, sources: list) -> bytes:
    """
    Return the report as PDF bytes using fpdf2.

    Parameters
    ----------
    topic   : research topic string.
    report  : full report markdown/text.
    sources : list of source URLs.

    Returns
    -------
    bytes – raw PDF content.

    Raises
    ------
    RuntimeError – if fpdf2 is not installed.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError(
            "fpdf2 is not installed. Run: pip install fpdf2"
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()

    # ---- Cover / header ----
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 51, 102)   # IBM navy
    pdf.cell(
        0, 10, "IBM Granite Research Agent",
        new_x="LMARGIN", new_y="NEXT", align="C"
    )

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 8, _latin1_safe(f"Research Topic: {topic}"), align="C", **_MC_KWARGS)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        new_x="LMARGIN", new_y="NEXT", align="C"
    )

    pdf.ln(4)
    pdf.set_draw_color(0, 51, 102)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # ---- Report body ----
    _render_markdown_to_pdf(pdf, report)

    # ---- Sources ----
    if sources:
        pdf.ln(4)
        pdf.set_draw_color(0, 51, 102)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 7, "Sources Consulted", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        for src in sources:
            src_clean = src.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 5, f"  - {src_clean}", **_MC_KWARGS)

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _render_markdown_to_pdf(pdf, text: str) -> None:
    """
    Naive markdown-to-PDF renderer for the report body.

    Handles:
      ## Heading  -> bold navy heading
      ### Sub     -> bold dark heading
      **bold**    -> stripped (plain text)
      - bullet    -> bullet point
      blank line  -> paragraph break

    All multi_cell calls include new_x/new_y for fpdf2 >= 2.9 compatibility.
    """
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("## "):
            heading = _latin1_safe(line[3:].strip())
            if not heading:
                continue
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 51, 102)
            pdf.multi_cell(0, 7, heading, **_MC_KWARGS)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)

        elif line.startswith("### "):
            heading = _latin1_safe(line[4:].strip())
            if not heading:
                continue
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(20, 60, 120)
            pdf.multi_cell(0, 6, heading, **_MC_KWARGS)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)

        elif line.startswith(("- ", "* ", "\u2022 ")):
            clean = _latin1_safe(_strip_markdown(line[2:].strip()))
            if clean:
                pdf.multi_cell(0, 5, f"  - {clean}", **_MC_KWARGS)

        elif line == "":
            pdf.ln(3)

        else:
            clean = _latin1_safe(_strip_markdown(line))
            if clean:
                pdf.multi_cell(0, 5, clean, **_MC_KWARGS)


def _strip_markdown(text: str) -> str:
    """Remove bold/italic markdown markers from a line."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text
