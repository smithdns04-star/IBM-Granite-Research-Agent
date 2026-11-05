"""
exporter.py – Professional PDF and TXT export using ReportLab.

Produces clean, IBM-styled PDF reports with proper headings, body text,
source tables and page numbers.  Falls back to fpdf2 if ReportLab is not
available (should not happen given requirements.txt).
"""

import io
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette (IBM Carbon)
# ---------------------------------------------------------------------------
_NAVY   = (0, 29, 108)    # #001d6c
_BLUE   = (0, 67, 206)    # #0043ce
_DARK   = (30, 30, 30)
_MUTED  = (80, 80, 80)
_WHITE  = (255, 255, 255)
_LIGHT  = (245, 247, 250)


# ---------------------------------------------------------------------------
# TXT export (no dependencies)
# ---------------------------------------------------------------------------

def export_txt(topic: str, report: str, sources: list) -> bytes:
    """Return the report as UTF-8 plain text bytes."""
    sep = "=" * 72
    lines = [
        sep,
        "IBM GRANITE RESEARCH STUDIO",
        sep,
        f"Research Topic : {topic}",
        f"Generated      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        sep,
        "",
        report,
        "",
    ]
    if sources:
        lines += [sep, "SOURCES CONSULTED", sep]
        for s in sources:
            lines.append(f"  - {s}")

    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# PDF export – ReportLab
# ---------------------------------------------------------------------------

def export_pdf(topic: str, report: str, sources: list) -> bytes:
    """
    Return the report as a professionally formatted PDF (bytes).

    Uses ReportLab for full Unicode support and clean typography.

    Raises
    ------
    RuntimeError – if ReportLab is not installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph, Spacer, HRFlowable, PageBreak,
            SimpleDocTemplate, Table, TableStyle,
        )
        from reportlab.platypus import ListItem, ListFlowable
    except ImportError:
        raise RuntimeError("ReportLab is not installed. Run: pip install reportlab")

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=f"Research Report – {topic}",
        author="IBM Granite Research Studio",
    )

    # ---- Styles ----
    rl_navy = colors.Color(_NAVY[0]/255, _NAVY[1]/255, _NAVY[2]/255)
    rl_blue = colors.Color(_BLUE[0]/255, _BLUE[1]/255, _BLUE[2]/255)

    title_style = ParagraphStyle(
        "Title", fontName="Helvetica-Bold", fontSize=20,
        textColor=rl_navy, spaceAfter=6, alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", fontName="Helvetica", fontSize=11,
        textColor=colors.Color(0.3, 0.3, 0.3), spaceAfter=4, alignment=TA_CENTER,
    )
    h2_style = ParagraphStyle(
        "H2", fontName="Helvetica-Bold", fontSize=13,
        textColor=rl_navy, spaceBefore=14, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=10,
        leading=16, spaceAfter=6, alignment=TA_JUSTIFY,
    )
    bullet_style = ParagraphStyle(
        "Bullet", fontName="Helvetica", fontSize=10,
        leading=14, leftIndent=16, spaceAfter=2,
    )
    caption_style = ParagraphStyle(
        "Caption", fontName="Helvetica", fontSize=8,
        textColor=colors.Color(0.4, 0.4, 0.4), alignment=TA_CENTER, spaceAfter=4,
    )

    story = []

    # ---- Cover block ----
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph("IBM Granite Research Studio", title_style))
    story.append(Paragraph(_rl_escape(topic), subtitle_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        caption_style,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=rl_blue))
    story.append(Spacer(1, 0.5 * cm))

    # ---- Report body ----
    for element in _parse_markdown(report, h2_style, body_style, bullet_style):
        story.append(element)

    # ---- Sources ----
    if sources:
        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_blue))
        story.append(Paragraph("Sources Consulted", h2_style))
        for i, src in enumerate(sources, 1):
            story.append(Paragraph(
                f"{i}. {_rl_escape(src)}",
                bullet_style,
            ))

    # ---- Build with page numbers ----
    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(*[c/255 for c in _MUTED])
        canvas.drawCentredString(
            A4[0] / 2, 1.2 * cm,
            f"IBM Granite Research Studio  |  Page {doc.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rl_escape(text: str) -> str:
    """Escape characters that would break ReportLab Paragraph XML parsing."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _parse_markdown(text: str, h2_style, body_style, bullet_style):
    """
    Yield ReportLab flowables parsed from simple markdown:
      ## Heading → h2
      - bullet   → bullet paragraph
      (blank)    → spacer
      other      → body paragraph
    """
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import cm

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            heading = _rl_escape(line[3:].strip())
            if heading:
                yield Paragraph(heading, h2_style)

        elif line.startswith("### "):
            heading = _rl_escape(line[4:].strip())
            if heading:
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib.enums import TA_LEFT
                rl_navy = (0, 29, 108)
                from reportlab.lib import colors as _colors
                sub_style = ParagraphStyle(
                    "H3", fontName="Helvetica-Bold", fontSize=11,
                    textColor=_colors.Color(rl_navy[0]/255, rl_navy[1]/255, rl_navy[2]/255),
                    spaceBefore=8, spaceAfter=3,
                )
                yield Paragraph(heading, sub_style)

        elif line.startswith(("- ", "* ", "• ")):
            content = _rl_escape(_strip_md(line[2:].strip()))
            if content:
                yield Paragraph(f"• {content}", bullet_style)

        elif re.match(r"^\d+\. ", line):
            content = _rl_escape(_strip_md(re.sub(r"^\d+\. ", "", line).strip()))
            if content:
                yield Paragraph(f"• {content}", bullet_style)

        elif line == "":
            yield Spacer(1, 0.15 * cm)

        else:
            content = _rl_escape(_strip_md(line))
            if content:
                yield Paragraph(content, body_style)


def _strip_md(text: str) -> str:
    """Remove bold/italic markdown markers."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text
