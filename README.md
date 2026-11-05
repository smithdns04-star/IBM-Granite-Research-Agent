# IBM Granite Research Studio

**An AI-Powered Research Assistant for Intelligent Knowledge Discovery**

Built with Python, Streamlit and IBM Granite running locally through Ollama.  
No paid APIs. No internet key required. Fully private and local.

---

## Features

| Page | Feature |
|---|---|
| 🏠 Dashboard | Stats overview, Granite status, recent activity |
| 💬 Research Assistant | Conversational Q&A with IBM Granite, persistent history |
| 📝 Report Generator | 14-section academic report from Wikipedia + OpenAlex + Crossref |
| 📄 Document Processing | Upload PDF/TXT/CSV/XLSX → summarise, ask questions |
| 📊 Data Analysis | CSV/XLSX statistics, histogram, bar, scatter and correlation charts |
| 💡 Research Insights | Findings, trends, gaps, future directions |
| 📚 Research Library | SQLite-backed report browser (search, view, export, delete) |
| 📤 Export Centre | ReportLab PDF and TXT downloads |
| ⚙️ Settings | Ollama URL/model config, source status, DB info |

---

## Technology Stack

| Component | Technology |
|---|---|
| Application framework | Streamlit |
| AI Model | IBM Granite 4.2 (via Ollama) |
| Background information | Wikipedia API (free) |
| Academic papers | OpenAlex API (free) |
| Publication metadata | Crossref API (free) |
| PDF reading | PyMuPDF |
| PDF generation | ReportLab |
| Data processing | Pandas |
| Charts | Matplotlib |
| Database | SQLite |

---

## Prerequisites

1. **Python 3.10 or higher**
2. **Ollama** — https://ollama.com/download (free, local)
3. **IBM Granite model** (pulled via Ollama)

---

## Windows Installation

Open PowerShell or Command Prompt in the project folder.

### Step 1 – Install Python dependencies

```
pip install -r requirements.txt
```

### Step 2 – Start Ollama

Open a **new terminal window** and run:

```
ollama serve
```

Leave this window open while using the application.

### Step 3 – Pull the Granite model *(first time only)*

```
ollama pull granite4.2:3b
```

### Step 4 – Run the application

```
python -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Configuration (optional)

Copy `.env.example` to `.env` and edit:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=granite4.2:3b
OPENALEX_EMAIL=your@email.com    # optional – higher rate limits
```

The `.env` file is listed in `.gitignore` and will not be committed.

---

## Project Structure

```
IBM_Granite_Research_Agent/
├── app.py                      # Main Streamlit application (9 pages)
├── main.py                     # CLI entry point (preserved)
├── requirements.txt
├── .env.example                # Configuration template
├── .gitignore
├── .streamlit/
│   └── config.toml             # IBM-styled theme
├── src/
│   ├── ollama_client.py        # Ollama/Granite connection
│   ├── information_search.py   # Wikipedia + OpenAlex + Crossref
│   ├── report_generator.py     # 14-section report prompt
│   ├── document_processor.py   # PDF/TXT/CSV/XLSX + Q&A
│   ├── data_analysis.py        # Pandas statistics + Matplotlib charts
│   ├── research_insights.py    # Insights extraction
│   ├── database.py             # SQLite storage
│   ├── exporter.py             # ReportLab PDF + TXT export
│   ├── research_agent.py       # Orchestrator (backwards-compatible)
│   └── library_manager.py      # Legacy file-based library (kept)
├── research_studio.db          # SQLite database (auto-created)
├── logs/
│   └── app.log
└── tests/
    ├── test_phase2.py
    └── tesy_research_agent.py
```

---

## Feature Demonstration Workflow

### 1. Dashboard
- Open the app. The Dashboard shows Granite status (should be green).
- Stats show total reports and documents.
- Quick Start Guide is available in the expander.

### 2. Research Assistant
- Click **Research Assistant**.
- Ask: *"What is the difference between supervised and unsupervised learning?"*
- Granite responds with a detailed answer.
- Ask a follow-up: *"Give me three real-world examples of each."*
- The conversation is saved and can be downloaded.

### 3. Report Generator
- Click **Report Generator**.
- Enter: *"Machine Learning in Healthcare"*
- Keep default options or choose a longer report.
- Click **Generate Report**. Progress bar shows each step:
  - Wikipedia search
  - OpenAlex academic papers
  - Crossref publications
  - Granite writing the 14-section report
- The report displays with a Sources Used tab (Wikipedia / OpenAlex / Crossref).
- Download as TXT or PDF immediately.

### 4. Document Processing
- Click **Document Processing**.
- Upload any PDF, TXT, CSV or XLSX file.
- Click **Summarise Document** → Granite writes a summary, key points and revision questions.
- Click the **Ask a Question** tab → ask *"What is the main conclusion?"*

### 5. Data Analysis
- Click **Data Analysis**.
- Upload a CSV file (e.g. a student marks spreadsheet).
- View Statistics tab: shape, column types, numeric summary.
- Charts tab: choose Histogram, Bar, Scatter or Correlation Matrix.
- AI Analysis tab: Granite interprets the dataset.

### 6. Research Insights
- After generating a report, click **Research Insights**.
- Select **Use last generated report** → click **Generate Insights**.
- See: Important Findings, Key Takeaways, Future Directions, AI Suggestions.

### 7. Research Library
- Click **Research Library**. All reports appear with dates.
- Search by keyword → filtered results.
- Click **Load** on a report to read it and download PDF/TXT.
- Click **Delete** to remove it.

### 8. Export Centre
- Click **Export Centre**.
- Choose a report from the dropdown.
- Preview the report, then click **Download as PDF** or **Download as TXT**.

### 9. Settings
- Click **Settings**.
- Change the Ollama URL or model name.
- See real-time API source status (Wikipedia / OpenAlex / Crossref).

---

## API Notes

| API | Key Required | Rate Limits |
|---|---|---|
| Wikipedia | None | Free |
| OpenAlex | None (email optional) | 10 req/s (100 with email) |
| Crossref | None | Reasonable use |

No paid subscriptions required for any feature.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Ollama: Offline" | Run `ollama serve` in a terminal |
| "Model not found" | Run `ollama pull granite4.2:3b` |
| Wikipedia returns 0 results | Transient API error — retry |
| PDF generation fails | Run `pip install reportlab` |
| CSV/XLSX loading error | Ensure file is not password-protected |
| Port 8501 in use | Run `python -m streamlit run app.py --server.port 8502` |
