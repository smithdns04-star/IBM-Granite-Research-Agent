"""
Research insights module.

Analyses a research report or raw text and extracts:
  - Important findings
  - Key takeaways
  - Future research directions
  - AI-generated suggestions (clearly labelled)
"""

import logging

from src.ollama_client import generate

logger = logging.getLogger(__name__)

_MAX_CHARS = 6000

_INSIGHTS_PROMPT = """You are an expert research analyst powered by IBM Granite.

Research Topic: {topic}

Research Content:
{content}

Analyse the research content and produce a structured insights report.
Use these EXACT section headings:

## Important Findings
List the 4–6 most significant findings from the research content.

## Key Takeaways
Summarise the 4–5 most important lessons or conclusions in plain language.

## Future Research Directions
Suggest 4–5 specific, actionable directions for future research on this topic.

## AI-Generated Suggestions
⚠️ NOTE: The following are AI-generated suggestions and may not reflect published research.
Provide 3–4 creative ideas or hypotheses related to this topic that are not explicitly in the content.

Keep responses grounded in the content for the first three sections.
Clearly distinguish the AI-generated section from evidence-based findings.
"""


def generate_insights(topic: str, content: str) -> str:
    """
    Generate research insights from a report or text block.

    Parameters
    ----------
    topic   : str – research topic label.
    content : str – the full report or text to analyse.

    Returns
    -------
    str – structured insights markdown.
    """
    truncated = content[:_MAX_CHARS]
    if len(content) > _MAX_CHARS:
        truncated += f"\n\n[Content truncated to {_MAX_CHARS} characters for processing.]"

    prompt = _INSIGHTS_PROMPT.format(topic=topic, content=truncated)

    logger.info("Generating insights for topic: %s", topic)
    result = generate(prompt, timeout=240)
    logger.info("Insights generated (%d chars)", len(result))
    return result
