"""
data_analysis.py – Dataset processing and chart generation.

Handles CSV and XLSX uploads, produces Pandas summaries, and renders
Matplotlib charts suitable for display inside Streamlit.
"""

import io
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # non-interactive backend for servers
import matplotlib.pyplot as plt
import pandas as pd

from src.ollama_client import generate

logger = logging.getLogger(__name__)

# Maximum rows sent to Granite for AI analysis
_MAX_AI_ROWS = 200


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_dataframe(uploaded_file) -> pd.DataFrame:
    """
    Read an uploaded CSV or XLSX file into a DataFrame.

    Parameters
    ----------
    uploaded_file : streamlit UploadedFile

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    ValueError   – unsupported file type
    RuntimeError – parse failure
    """
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    raw = uploaded_file.read()

    try:
        if name.endswith(".csv"):
            # Try UTF-8 then latin-1
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(raw))
        else:
            raise ValueError(
                f"Unsupported file type: '{uploaded_file.name}'. "
                "Please upload CSV or XLSX."
            )
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Could not parse dataset '{uploaded_file.name}': {exc}") from exc

    if df.empty:
        raise RuntimeError("The uploaded dataset is empty.")

    logger.info(
        "Loaded dataset '%s': %d rows × %d cols",
        uploaded_file.name, len(df), len(df.columns),
    )
    return df


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def describe_dataframe(df: pd.DataFrame) -> dict:
    """
    Return a structured summary of the DataFrame.

    Returns
    -------
    dict with keys:
        shape, dtypes, missing, numeric_summary (DataFrame), preview (DataFrame)
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return {
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isnull().sum().to_dict(),
        "numeric_summary": df[numeric_cols].describe() if numeric_cols else pd.DataFrame(),
        "preview": df.head(10),
        "numeric_columns": numeric_cols,
        "categorical_columns": df.select_dtypes(exclude="number").columns.tolist(),
    }


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def _new_fig(title: str = ""):
    """Create a clean, IBM-styled Matplotlib figure."""
    fig, ax = plt.subplots(figsize=(9, 4))
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color="#001d6c", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#333333")
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8f9fb")
    return fig, ax


def chart_histogram(df: pd.DataFrame, column: str) -> io.BytesIO:
    """Return a PNG BytesIO of a histogram for *column*."""
    fig, ax = _new_fig(f"Distribution of {column}")
    ax.hist(df[column].dropna(), bins=20, color="#0043ce", edgecolor="white", alpha=0.85)
    ax.set_xlabel(column, fontsize=10)
    ax.set_ylabel("Frequency", fontsize=10)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_bar(df: pd.DataFrame, x_col: str, y_col: str) -> io.BytesIO:
    """Return a PNG BytesIO of a bar chart."""
    plot_df = df[[x_col, y_col]].dropna().head(20)
    fig, ax = _new_fig(f"{y_col} by {x_col}")
    ax.bar(plot_df[x_col].astype(str), plot_df[y_col], color="#0043ce", alpha=0.85)
    ax.set_xlabel(x_col, fontsize=10)
    ax.set_ylabel(y_col, fontsize=10)
    plt.xticks(rotation=35, ha="right", fontsize=8)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_scatter(df: pd.DataFrame, x_col: str, y_col: str) -> io.BytesIO:
    """Return a PNG BytesIO of a scatter plot."""
    plot_df = df[[x_col, y_col]].dropna()
    fig, ax = _new_fig(f"{y_col} vs {x_col}")
    ax.scatter(plot_df[x_col], plot_df[y_col], color="#0043ce", alpha=0.6, s=20)
    ax.set_xlabel(x_col, fontsize=10)
    ax.set_ylabel(y_col, fontsize=10)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_correlation(df: pd.DataFrame) -> io.BytesIO | None:
    """Return a PNG BytesIO of a correlation heatmap, or None if < 2 numeric cols."""
    numeric = df.select_dtypes(include="number")
    if len(numeric.columns) < 2:
        return None
    corr = numeric.corr()
    fig, ax = _new_fig("Correlation Matrix")
    im = ax.imshow(corr, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    plt.colorbar(im, ax=ax)
    for i in range(len(corr)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# AI-powered dataset analysis
# ---------------------------------------------------------------------------

_DATASET_PROMPT = """You are a data analyst powered by IBM Granite.

Dataset: {filename}
Shape: {rows} rows × {cols} columns
Columns: {columns}

Sample data (first {sample_rows} rows):
{sample}

Numeric summary:
{numeric_summary}

Provide a structured analysis using these EXACT headings:

## Dataset Overview
Describe what this dataset appears to contain and its purpose.

## Key Observations
List 4–6 notable observations from the data.

## Statistical Insights
Interpret the numeric summary statistics meaningfully.

## Data Quality Notes
Comment on missing values, outliers or potential issues.

## Suggested Analyses
Suggest 3–4 further analyses or visualisations that would be valuable.

Base all observations on the data provided. Do not invent statistics.
"""


def analyse_dataset(filename: str, df: pd.DataFrame) -> str:
    """
    Use IBM Granite to produce a natural-language analysis of *df*.

    Returns
    -------
    str – structured analysis markdown.
    """
    sample_df = df.head(min(_MAX_AI_ROWS, len(df)))
    numeric = df.select_dtypes(include="number")

    prompt = _DATASET_PROMPT.format(
        filename=filename,
        rows=len(df),
        cols=len(df.columns),
        columns=", ".join(df.columns.tolist()),
        sample_rows=len(sample_df),
        sample=sample_df.to_string(max_rows=20, max_cols=10),
        numeric_summary=(
            numeric.describe().to_string() if not numeric.empty else "No numeric columns."
        ),
    )

    logger.info("Analysing dataset '%s' with Granite", filename)
    return generate(prompt, timeout=240)
