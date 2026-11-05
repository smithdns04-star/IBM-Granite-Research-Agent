"""
document_processor.py – Document upload, text extraction and AI analysis.

Supported formats:
  PDF   – text extraction via PyMuPDF
  TXT   – plain text
  CSV   – loaded as text table via pandas
  XLSX  – loaded as text table via pandas

Features:
  - Chunked processing for large documents
  - AI summarisation via IBM Granite
  - Q&A about uploaded document content
"""

import io
import logging
import re

import pandas as pd

from src.ollama_client import generate

logger = logging.getLogger(__name__)

# Maximum characters per chunk sent to the model
_CHUNK_SIZE = 6000
# Maximum characters of full text sent for summarisation
_MAX_CHARS = 8000


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(uploaded_file) -> str:
    """
    Extract plain text from a Streamlit UploadedFile.

    Supports .pdf, .txt, .csv, .xlsx/.xls

    Returns
    -------
    str – extracted text content.

    Raises
    ------
    ValueError   – unsupported file type.
    RuntimeError – extraction failed.
    """
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return _extract_pdf(uploaded_file)
    elif name.endswith(".txt"):
        return _extract_txt(uploaded_file)
    elif name.endswith(".csv"):
        return _extract_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        return _extract_xlsx(uploaded_file)
    else:
        raise ValueError(
            f"Unsupported file type: '{uploaded_file.name}'. "
            "Please upload PDF, TXT, CSV or XLSX."
        )


def _extract_pdf(uploaded_file) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = [page.get_text() for page in doc]
        doc.close()
        full_text = "\n".join(pages_text).strip()

        if not full_text:
            raise RuntimeError(
                "No readable text found in the PDF. "
                "The file may be scanned or image-based."
            )
        return full_text

    except (ImportError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc


def _extract_txt(uploaded_file) -> str:
    """Extract text from a plain-text file."""
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        try:
            return raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return raw.decode("latin-1").strip()
    except Exception as exc:
        raise RuntimeError(f"TXT extraction failed: {exc}") from exc


def _extract_csv(uploaded_file) -> str:
    """Read CSV and return a text representation."""
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        return f"CSV Dataset: {uploaded_file.name}\n\n{df.to_string(max_rows=100, max_cols=15)}"
    except Exception as exc:
        raise RuntimeError(f"CSV extraction failed: {exc}") from exc


def _extract_xlsx(uploaded_file) -> str:
    """Read XLSX and return a text representation."""
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        df = pd.read_excel(io.BytesIO(raw))
        return f"Excel Dataset: {uploaded_file.name}\n\n{df.to_string(max_rows=100, max_cols=15)}"
    except Exception as exc:
        raise RuntimeError(f"XLSX extraction failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Chunked processing helpers
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE) -> list[str]:
    """Split *text* into overlapping chunks of *chunk_size* characters."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    overlap = chunk_size // 10  # 10% overlap
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# AI summarisation
# ---------------------------------------------------------------------------

_SUMMARY_PROMPT = """You are an expert academic document analyst powered by IBM Granite.

Document: {filename}

Content:
{content}

Analyse the document and respond with these EXACT headings:

## Summary
Write a concise 3–5 paragraph summary.

## Key Points
List the 5–8 most important points as bullet points.

## Important Findings
Describe significant findings, results or conclusions.

## Difficult Terms Explained
Briefly define 3–5 technical or complex terms found in the document.

## Revision Questions
Generate 5 study questions a student could use to review this material.

Keep analysis grounded in the document. Do not add external information.
"""


def summarize_document(filename: str, text: str) -> str:
    """
    Generate an AI summary of a document.

    For large documents, only the first _MAX_CHARS characters are analysed;
    a truncation notice is appended to the prompt.

    Returns
    -------
    str – structured summary markdown.
    """
    truncated = text[:_MAX_CHARS]
    notice = ""
    if len(text) > _MAX_CHARS:
        notice = (
            f"\n\n[NOTE: Document truncated to {_MAX_CHARS:,} chars "
            f"out of {len(text):,} total for processing.]"
        )

    prompt = _SUMMARY_PROMPT.format(
        filename=filename,
        content=truncated + notice,
    )

    logger.info("Summarising '%s' (%d chars)", filename, len(text))
    result = generate(prompt, timeout=240)
    logger.info("Summary generated (%d chars)", len(result))
    return result


# ---------------------------------------------------------------------------
# Document Q&A
# ---------------------------------------------------------------------------

_QA_PROMPT = """You are a knowledgeable research assistant powered by IBM Granite.

Document: {filename}

Document Content:
{content}

User Question: {question}

Answer the question based strictly on the document content provided.
If the answer is not in the document, say: "This information is not found in the provided document."
Provide a clear, concise answer followed by relevant supporting quotes or paraphrases from the document.
"""


def answer_question(filename: str, text: str, question: str) -> str:
    """
    Answer a question about a document using IBM Granite.

    Uses the first _MAX_CHARS characters of the document.

    Returns
    -------
    str – answer text.
    """
    if not question.strip():
        raise ValueError("Please enter a question.")

    truncated = text[:_MAX_CHARS]
    prompt = _QA_PROMPT.format(
        filename=filename,
        content=truncated,
        question=question,
    )

    logger.info("Q&A on '%s': %s", filename, question[:80])
    return generate(prompt, timeout=180)
