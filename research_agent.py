"""
Research agent orchestrator.

Coordinates information search, report generation and library storage.
Preserved from original; updated to use the new library_manager and
ollama_client modules.
"""

import logging
from pathlib import Path

from src.information_search import search_information
from src.report_generator import generate_report
from src.library_manager import save_report

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_research(topic: str) -> tuple:
    """
    Run the full research pipeline for *topic*.

    Returns
    -------
    report      : str  – full report text.
    sources     : list – source URLs.
    report_path : str  – absolute path to the saved report file.
    """
    logger.info("Research started: %s", topic)

    information, sources = search_information(topic)
    report = generate_report(topic, information)
    report_path = save_report(topic, report, sources)

    logger.info("Research completed successfully: %s", topic)
    return report, sources, report_path
