"""
IBM Granite Research Studio
===========================
Professional AI-powered research assistant using IBM Granite via Ollama.

Pages
-----
1.  Dashboard           – stats, status, recent activity
2.  Research Assistant  – free-form Q&A with Granite, conversation history
3.  Report Generator    – 14-section academic report from multi-source search
4.  Document Processing – upload PDF/TXT/CSV/XLSX, summarise, Q&A
5.  Data Analysis       – CSV/XLSX dataset explorer with charts
6.  Research Insights   – findings, trends, gaps, suggestions
7.  Research Library    – SQLite-backed report browser
8.  Export Centre       – ReportLab PDF and TXT downloads
9.  Settings            – model config, source status
"""

import logging
import uuid
from pathlib import Path

import streamlit as st

# ── Page config – MUST be first Streamlit call ────────────────────────────
st.set_page_config(
    page_title="IBM Granite Research Studio",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Logging ───────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=_LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Ensure upload / reports dirs exist ───────────────────────────────────
(Path(__file__).resolve().parent / "uploads").mkdir(exist_ok=True)
(Path(__file__).resolve().parent / "reports").mkdir(exist_ok=True)

# ── Global CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html,body,[data-testid="stAppViewContainer"]{
    background:#f5f7fa;
    font-family:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;
}
/* ── Sidebar ── */
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#001d6c 0%,#0043ce 100%);
}
[data-testid="stSidebar"] *{color:#ffffff !important;}
[data-testid="stSidebar"] .stRadio label{font-size:15px;padding:3px 0;}
/* ── Header banner ── */
.ibm-banner{
    background:#0043ce;color:#fff;
    padding:16px 28px 12px;border-radius:8px;margin-bottom:20px;
}
.ibm-banner h1{margin:0;font-size:28px;font-weight:700;letter-spacing:.3px;}
.ibm-banner p{margin:4px 0 0;font-size:13px;opacity:.88;}
/* ── Cards ── */
.ibm-card{
    background:#fff;border:1px solid #dde1e7;
    border-radius:8px;padding:18px 22px;margin-bottom:14px;
}
.ibm-card h3{margin-top:0;color:#001d6c;font-size:15px;}
/* ── Section titles ── */
.sec-title{
    color:#001d6c;font-size:18px;font-weight:700;
    border-bottom:3px solid #0043ce;padding-bottom:5px;margin-bottom:16px;
}
/* ── Feature tiles ── */
.ftile{
    background:#fff;border-left:5px solid #0043ce;
    border-radius:6px;padding:13px 17px;margin-bottom:11px;
}
.ftile h4{margin:0 0 3px;color:#001d6c;font-size:14px;}
.ftile p{margin:0;color:#525252;font-size:12px;}
/* ── Stat cards ── */
.stat-card{
    background:#fff;border:1px solid #dde1e7;border-radius:8px;
    padding:16px 20px;text-align:center;
}
.stat-card .num{font-size:32px;font-weight:700;color:#0043ce;}
.stat-card .lbl{font-size:12px;color:#525252;margin-top:2px;}
/* ── Source badge ── */
.badge-wiki{background:#e8f4fd;color:#005a9e;
    border-radius:4px;padding:2px 7px;font-size:11px;font-weight:600;}
.badge-oa{background:#e6f4ea;color:#1a6b35;
    border-radius:4px;padding:2px 7px;font-size:11px;font-weight:600;}
.badge-cr{background:#fff3e0;color:#b35c00;
    border-radius:4px;padding:2px 7px;font-size:11px;font-weight:600;}
/* ── Report body ── */
.report-body{
    background:#fff;border:1px solid #dde1e7;border-radius:8px;
    padding:22px 26px;line-height:1.75;
}
/* ── Buttons ── */
.stButton>button{
    background:#0043ce;color:#fff;border:none;
    border-radius:4px;font-weight:600;padding:7px 20px;
}
.stButton>button:hover{background:#0035a7;}
/* ── Chat bubbles ── */
.chat-user{
    background:#e8f0fe;border-radius:10px 10px 2px 10px;
    padding:10px 14px;margin:6px 0;font-size:14px;
}
.chat-assistant{
    background:#fff;border:1px solid #dde1e7;
    border-radius:10px 10px 10px 2px;
    padding:10px 14px;margin:6px 0;font-size:14px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────

def banner(title: str, subtitle: str = "") -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="ibm-banner"><h1>{title}</h1>{sub}</div>',
                unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<div class="sec-title">{label}</div>', unsafe_allow_html=True)


def card(html: str) -> None:
    st.markdown(f'<div class="ibm-card">{html}</div>', unsafe_allow_html=True)


def _status() -> dict:
    if "ollama_status" not in st.session_state:
        from src.ollama_client import get_status
        st.session_state["ollama_status"] = get_status()
    return st.session_state["ollama_status"]


def _clear_status() -> None:
    st.session_state.pop("ollama_status", None)


def _require_model() -> bool:
    """Return True if Granite is ready; else show error and return False."""
    s = _status()
    if not s["ollama_online"]:
        st.error("❌ Ollama is offline. Run `ollama serve` in a terminal.")
        return False
    if not s["model_available"]:
        from src.ollama_client import OLLAMA_MODEL
        st.warning(
            f"⚠️ Model **{OLLAMA_MODEL}** not found. "
            f"Pull it: `ollama pull {OLLAMA_MODEL}`"
        )
        return False
    return True


def _src_badge(src_type: str) -> str:
    mapping = {
        "wikipedia": '<span class="badge-wiki">Wikipedia</span>',
        "openalex":  '<span class="badge-oa">OpenAlex</span>',
        "crossref":  '<span class="badge-cr">Crossref</span>',
    }
    return mapping.get(src_type.lower(), f'<span>{src_type}</span>')


def _session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
    return st.session_state["session_id"]


# ── Sidebar ───────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔬 IBM Granite\n**Research Studio**")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Dashboard",
            "💬 Research Assistant",
            "📝 Report Generator",
            "📄 Document Processing",
            "📊 Data Analysis",
            "💡 Research Insights",
            "📚 Research Library",
            "📤 Export Centre",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    s = _status()
    if s["ollama_online"] and s["model_available"]:
        st.markdown("🟢 **Granite: Ready**")
        st.caption(f"Model: {s['model_name']}")
    elif s["ollama_online"]:
        st.markdown("🟡 **Ollama: Online**")
        st.caption("Model not found")
    else:
        st.markdown("🔴 **Ollama: Offline**")
        st.caption("Run: ollama serve")

    if st.button("🔄 Refresh", use_container_width=True):
        _clear_status()
        st.rerun()

    st.markdown("---")
    st.caption("IBM Granite 4.2 · Ollama · Streamlit")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1 – DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

if page == "🏠 Dashboard":
    banner(
        "IBM Granite Research Studio",
        "An AI-Powered Research Assistant for Intelligent Knowledge Discovery",
    )

    # -- Stats row --
    from src.database import get_stats, init_db
    init_db()
    stats = get_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="num">{stats["total_reports"]}</div>'
            '<div class="lbl">Research Reports</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="num">{stats["total_documents"]}</div>'
            '<div class="lbl">Documents Processed</div></div>',
            unsafe_allow_html=True,
        )
    s = _status()
    with c3:
        status_icon = "🟢" if (s["ollama_online"] and s["model_available"]) else ("🟡" if s["ollama_online"] else "🔴")
        status_text = "Online" if (s["ollama_online"] and s["model_available"]) else ("Partial" if s["ollama_online"] else "Offline")
        st.markdown(
            f'<div class="stat-card"><div class="num">{status_icon}</div>'
            f'<div class="lbl">Granite: {status_text}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            '<div class="stat-card"><div class="num">3</div>'
            '<div class="lbl">Research Sources</div></div>',
            unsafe_allow_html=True,
        )

    # -- Status detail --
    st.markdown("<br>", unsafe_allow_html=True)
    section("System Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        if s["ollama_online"]:
            st.success("✅ Ollama Server: Online")
        else:
            st.error("❌ Ollama Server: Offline")
            st.code("ollama serve", language=None)
    with col2:
        if s["model_available"]:
            st.success(f"✅ Model: {s['model_name']}")
        else:
            st.warning("⚠️ Granite Model: Not Found")
            from src.ollama_client import OLLAMA_MODEL
            st.code(f"ollama pull {OLLAMA_MODEL}", language=None)
    with col3:
        avail = s.get("available_models", [])
        if avail:
            st.info(f"📦 {len(avail)} model(s) in Ollama")
            with st.expander("View models"):
                for m in avail:
                    st.code(m, language=None)
        else:
            st.warning("No models found in Ollama.")

    # -- Feature tiles --
    st.markdown("<br>", unsafe_allow_html=True)
    section("Application Features")
    features = [
        ("💬 Research Assistant",
         "Ask any research question. IBM Granite provides detailed AI answers with conversation history."),
        ("📝 Report Generator",
         "Enter a topic → fetches Wikipedia, OpenAlex & Crossref → Granite writes a 14-section academic report."),
        ("📄 Document Processing",
         "Upload PDF, TXT, CSV or XLSX → extract text → AI summary, key points, revision Q&A."),
        ("📊 Data Analysis",
         "Upload CSV/XLSX → automatic statistics, correlation matrix and interactive charts."),
        ("💡 Research Insights",
         "Extract key findings, trends, research gaps and AI-generated future directions."),
        ("📚 Research Library",
         "SQLite-backed history of all reports. Search, view, export and delete."),
        ("📤 Export Centre",
         "Download any report as a professionally formatted PDF (ReportLab) or TXT file."),
    ]
    cols = st.columns(2)
    for i, (title_ft, desc) in enumerate(features):
        with cols[i % 2]:
            st.markdown(
                f'<div class="ftile"><h4>{title_ft}</h4><p>{desc}</p></div>',
                unsafe_allow_html=True,
            )

    # -- Recent activity --
    st.markdown("<br>", unsafe_allow_html=True)
    section("Recent Research Activity")
    if stats["recent_topics"]:
        for r in stats["recent_topics"]:
            card(
                f'<h3>📋 {r["topic"]}</h3>'
                f'<p style="color:#525252;font-size:12px;">Generated: {r["created_at"]}</p>'
            )
    else:
        st.info("No reports yet. Use **Report Generator** to create your first report.")

    with st.expander("📖 Quick Start Guide"):
        st.markdown("""
**1. Start Ollama** (run in a separate terminal):
```
ollama serve
```
**2. Confirm your model** (first time only):
```
ollama pull granite4.2:3b
```
**3. Run the application**:
```
python -m streamlit run app.py
```
**4. Generate a report** → click **Report Generator** → enter a topic → click Generate.

**5. Export** → click **Export Centre** → select report → Download PDF.
        """)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2 – RESEARCH ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════

elif page == "💬 Research Assistant":
    banner("Research Assistant",
           "Ask research questions · Get AI-powered answers · Build a conversation")

    if not _require_model():
        st.stop()

    from src.ollama_client import generate as granite_generate
    from src.database import save_message, get_conversation, clear_conversation

    sid = _session_id()

    # -- Conversation display --
    section("Conversation")
    history = get_conversation(sid)

    if not history:
        st.info("Start by asking a research question below.")
    else:
        for msg in history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">🧑 <strong>You:</strong> {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-assistant">🤖 <strong>Granite:</strong><br>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # -- Input --
    section("Ask a Question")
    question = st.text_area(
        "Your question",
        placeholder="e.g. What are the main applications of transformer models in NLP?",
        height=100,
        label_visibility="collapsed",
    )

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_btn = st.button("Ask Granite", type="primary", use_container_width=True)
    with col_clear:
        clear_btn = st.button("Clear Chat", use_container_width=True)

    if clear_btn:
        clear_conversation(sid)
        st.rerun()

    if ask_btn:
        if not question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            # Build context from last 6 turns
            prior = get_conversation(sid)
            context = ""
            if prior:
                context_turns = prior[-6:]
                context = "\n".join(
                    f"{'User' if t['role']=='user' else 'Assistant'}: {t['content']}"
                    for t in context_turns
                )
                context = f"Previous conversation:\n{context}\n\n"

            prompt = (
                f"{context}"
                f"You are an expert academic research assistant powered by IBM Granite.\n\n"
                f"User question: {question}\n\n"
                f"Provide a detailed, accurate, well-structured answer. "
                f"If referencing facts, note they should be verified against primary sources."
            )

            with st.spinner("IBM Granite is thinking…"):
                try:
                    answer = granite_generate(prompt, timeout=180)
                    save_message(sid, "user", question)
                    save_message(sid, "assistant", answer)
                    st.rerun()
                except RuntimeError as e:
                    st.error(f"❌ {e}")

    # -- Save conversation --
    if history:
        from src.exporter import export_txt
        conv_text = "\n\n".join(
            f"{'You' if m['role']=='user' else 'Granite'}: {m['content']}"
            for m in history
        )
        st.download_button(
            "⬇️ Download Conversation",
            data=export_txt("Research Conversation", conv_text, []),
            file_name="conversation.txt",
            mime="text/plain",
        )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3 – REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📝 Report Generator":
    banner("Report Generator",
           "Topic → Multi-source search → 14-section AI academic report")

    if not _require_model():
        st.stop()

    section("Research Topic")
    topic = st.text_input(
        "Topic",
        placeholder="e.g. Quantum Computing in Cryptography",
        label_visibility="collapsed",
    )

    with st.expander("⚙️ Report Options"):
        col_l, col_w, col_a = st.columns(3)
        with col_l:
            length = st.selectbox(
                "Report length",
                ["Short (500–800 words)", "Standard (1000–1500 words)",
                 "Detailed (2000–2500 words)", "Comprehensive (3000+ words)"],
                index=1,
            )
        with col_w:
            max_wiki = st.slider("Wikipedia pages", 2, 6, 3)
        with col_a:
            max_acad = st.slider("Academic papers per source", 2, 8, 4)

    gen_btn = st.button("Generate Report", type="primary")

    if gen_btn:
        if not topic.strip():
            st.warning("⚠️ Please enter a research topic.")
        else:
            prog = st.progress(0, text="Starting…")
            try:
                prog.progress(10, text="🔍 Searching Wikipedia…")
                from src.information_search import search_all_sources
                search_result = search_all_sources(
                    topic, max_wiki=max_wiki, max_academic=max_acad
                )
                info = search_result["all"]
                sources = search_result["sources"]

                # Show any source errors as warnings (not stoppers)
                for err in search_result["errors"]:
                    st.warning(f"⚠️ {err}")

                wiki_count = len(search_result["wikipedia"])
                oa_count = len(search_result["openalex"])
                cr_count = len(search_result["crossref"])
                prog.progress(35, text=
                    f"✅ Found {wiki_count} Wikipedia + "
                    f"{oa_count} OpenAlex + {cr_count} Crossref sources. "
                    "Sending to IBM Granite…"
                )

                from src.report_generator import generate_report
                report = generate_report(topic, info, length=length)

                prog.progress(85, text="💾 Saving to library…")
                from src.database import save_report
                report_id = save_report(
                    topic, report, sources,
                    wiki_sources=[i["url"] for i in search_result["wikipedia"]],
                    academic_sources=[i["url"] for i in search_result["openalex"] + search_result["crossref"]],
                )

                prog.progress(100, text="✅ Report complete!")

                # Cache in session
                st.session_state["last_topic"] = topic
                st.session_state["last_report"] = report
                st.session_state["last_sources"] = sources
                st.session_state["last_info"] = info

                st.success(f"✅ Report saved to library (ID: {report_id})")

                # -- Display report --
                section("Generated Report")
                st.markdown(
                    f'<div class="report-body">{report}</div>',
                    unsafe_allow_html=True,
                )

                # -- Sources used --
                section("Sources Used")
                tab_wiki, tab_oa, tab_cr = st.tabs(["Wikipedia", "OpenAlex", "Crossref"])

                with tab_wiki:
                    if search_result["wikipedia"]:
                        for s_item in search_result["wikipedia"]:
                            st.markdown(f"- [{s_item['title']}]({s_item['url']})")
                    else:
                        st.info("No Wikipedia sources retrieved.")

                with tab_oa:
                    if search_result["openalex"]:
                        for s_item in search_result["openalex"]:
                            auth = f" — {s_item['authors']}" if s_item.get("authors") else ""
                            yr = f" ({s_item['year']})" if s_item.get("year") else ""
                            jrn = f", *{s_item['journal']}*" if s_item.get("journal") else ""
                            st.markdown(
                                f"- [{s_item['title']}]({s_item['url']}){auth}{yr}{jrn}"
                            )
                    else:
                        st.info("No OpenAlex sources retrieved.")

                with tab_cr:
                    if search_result["crossref"]:
                        for s_item in search_result["crossref"]:
                            auth = f" — {s_item['authors']}" if s_item.get("authors") else ""
                            yr = f" ({s_item['year']})" if s_item.get("year") else ""
                            jrn = f", *{s_item['journal']}*" if s_item.get("journal") else ""
                            st.markdown(
                                f"- [{s_item['title']}]({s_item['url']}){auth}{yr}{jrn}"
                            )
                    else:
                        st.info("No Crossref sources retrieved.")

                # -- Quick download --
                section("Quick Download")
                from src.exporter import export_txt, export_pdf
                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "⬇️ TXT",
                        data=export_txt(topic, report, sources),
                        file_name=f"{topic[:40].replace(' ','_')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with dl2:
                    try:
                        st.download_button(
                            "⬇️ PDF",
                            data=export_pdf(topic, report, sources),
                            file_name=f"{topic[:40].replace(' ','_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except RuntimeError as e:
                        st.warning(f"PDF unavailable: {e}")

            except ValueError as e:
                prog.empty(); st.warning(f"⚠️ {e}")
            except RuntimeError as e:
                prog.empty(); st.error(f"❌ {e}")
            except Exception as e:
                prog.empty(); st.error(f"❌ Unexpected error: {e}")
                logger.exception("Report generation failed")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 4 – DOCUMENT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📄 Document Processing":
    banner("Document Processing",
           "Upload PDF, TXT, CSV or XLSX → AI-powered analysis and Q&A")

    if not _require_model():
        st.stop()

    section("Upload Document")
    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "csv", "xlsx", "xls"],
        help="PDF, TXT, CSV or XLSX – max 50 MB",
    )

    if not uploaded:
        card(
            "<h3>How to use Document Processing</h3>"
            "<ol>"
            "<li>Click <strong>Browse files</strong> above.</li>"
            "<li>Select a PDF, TXT, CSV or XLSX file.</li>"
            "<li>Click <strong>Summarise Document</strong>.</li>"
            "<li>Use the Q&amp;A section to ask questions about the document.</li>"
            "</ol>"
        )
    else:
        st.info(f"📎 **{uploaded.name}** ({uploaded.size:,} bytes)")
        from src.document_processor import extract_text, summarize_document, answer_question

        tab_sum, tab_qa = st.tabs(["📋 Summarise", "❓ Ask a Question"])

        with tab_sum:
            sum_btn = st.button("Summarise Document", type="primary")
            if sum_btn:
                prog = st.progress(0, text="Extracting text…")
                try:
                    uploaded.seek(0)
                    prog.progress(20, "📖 Extracting text…")
                    text = extract_text(uploaded)
                    st.success(f"✅ Extracted {len(text):,} characters.")

                    with st.expander("📄 View extracted text (first 2000 chars)"):
                        st.text(text[:2000] + ("…" if len(text) > 2000 else ""))

                    prog.progress(50, "🤖 Sending to IBM Granite…")
                    summary = summarize_document(uploaded.name, text)
                    prog.progress(100, "✅ Done!")

                    # Save to DB
                    from src.database import save_document
                    save_document(uploaded.name, uploaded.name.rsplit(".", 1)[-1].upper(),
                                  len(text), summary)

                    # Cache for Q&A and Insights
                    st.session_state["doc_name"] = uploaded.name
                    st.session_state["doc_text"] = text
                    st.session_state["doc_summary"] = summary

                    section("Document Analysis")
                    st.markdown(
                        f'<div class="report-body">{summary}</div>',
                        unsafe_allow_html=True,
                    )

                    from src.exporter import export_txt
                    st.download_button(
                        "⬇️ Download Summary",
                        data=export_txt(uploaded.name, summary, [f"Document: {uploaded.name}"]),
                        file_name=f"{uploaded.name}_summary.txt",
                        mime="text/plain",
                    )

                except (ValueError, RuntimeError) as e:
                    prog.empty(); st.error(f"❌ {e}")
                except Exception as e:
                    prog.empty(); st.error(f"❌ {e}")
                    logger.exception("Document summary failed")

        with tab_qa:
            # Need doc text – either from this run or cached
            if "doc_text" not in st.session_state or st.session_state.get("doc_name") != uploaded.name:
                st.info("Summarise the document first to load it into memory, then ask questions here.")
            else:
                q = st.text_input("Ask a question about the document",
                                  placeholder="e.g. What is the main conclusion?")
                qa_btn = st.button("Get Answer", type="primary")
                if qa_btn:
                    if not q.strip():
                        st.warning("⚠️ Please enter a question.")
                    else:
                        with st.spinner("IBM Granite is reading the document…"):
                            try:
                                answer = answer_question(
                                    st.session_state["doc_name"],
                                    st.session_state["doc_text"],
                                    q,
                                )
                                st.markdown(
                                    f'<div class="chat-assistant">🤖 <strong>Answer:</strong><br>{answer}</div>',
                                    unsafe_allow_html=True,
                                )
                            except RuntimeError as e:
                                st.error(f"❌ {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 5 – DATA ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📊 Data Analysis":
    banner("Data Analysis", "Upload CSV or XLSX → statistics, charts and AI insights")

    section("Upload Dataset")
    ds_file = st.file_uploader(
        "Choose CSV or XLSX",
        type=["csv", "xlsx", "xls"],
        key="ds_uploader",
    )

    if not ds_file:
        card(
            "<h3>How to use Data Analysis</h3>"
            "<ol>"
            "<li>Upload a CSV or XLSX dataset.</li>"
            "<li>View automatic statistics and column types.</li>"
            "<li>Choose columns to plot charts.</li>"
            "<li>Click <strong>AI Analysis</strong> for IBM Granite insights.</li>"
            "</ol>"
        )
    else:
        from src.data_analysis import (
            load_dataframe, describe_dataframe,
            chart_histogram, chart_bar, chart_scatter, chart_correlation,
            analyse_dataset,
        )

        try:
            ds_file.seek(0)
            df = load_dataframe(ds_file)
        except (ValueError, RuntimeError) as e:
            st.error(f"❌ {e}")
            st.stop()

        desc = describe_dataframe(df)
        st.success(
            f"✅ Loaded **{ds_file.name}** — "
            f"{desc['shape'][0]:,} rows × {desc['shape'][1]} columns"
        )

        tab_stats, tab_charts, tab_ai = st.tabs(["📈 Statistics", "📊 Charts", "🤖 AI Analysis"])

        with tab_stats:
            section("Dataset Preview")
            st.dataframe(desc["preview"], use_container_width=True)

            section("Column Information")
            import pandas as pd
            dtype_df = pd.DataFrame({
                "Column": list(desc["dtypes"].keys()),
                "Type": list(desc["dtypes"].values()),
                "Missing": [desc["missing"].get(c, 0) for c in desc["dtypes"]],
            })
            st.dataframe(dtype_df, use_container_width=True)

            if not desc["numeric_summary"].empty:
                section("Numeric Statistics")
                st.dataframe(desc["numeric_summary"], use_container_width=True)

        with tab_charts:
            num_cols = desc["numeric_columns"]
            cat_cols = desc["categorical_columns"]

            if not num_cols:
                st.info("No numeric columns found for charting.")
            else:
                chart_type = st.radio(
                    "Chart type",
                    ["Histogram", "Bar Chart", "Scatter Plot", "Correlation Matrix"],
                    horizontal=True,
                )

                if chart_type == "Histogram":
                    col = st.selectbox("Column", num_cols)
                    buf = chart_histogram(df, col)
                    st.image(buf, use_container_width=True)

                elif chart_type == "Bar Chart":
                    if not cat_cols:
                        st.info("Bar chart requires at least one categorical column.")
                    else:
                        x_col = st.selectbox("X axis (category)", cat_cols)
                        y_col = st.selectbox("Y axis (numeric)", num_cols)
                        buf = chart_bar(df, x_col, y_col)
                        st.image(buf, use_container_width=True)

                elif chart_type == "Scatter Plot":
                    if len(num_cols) < 2:
                        st.info("Scatter plot requires at least 2 numeric columns.")
                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            x_col = st.selectbox("X axis", num_cols, key="sc_x")
                        with c2:
                            y_col = st.selectbox("Y axis", num_cols, index=1, key="sc_y")
                        buf = chart_scatter(df, x_col, y_col)
                        st.image(buf, use_container_width=True)

                elif chart_type == "Correlation Matrix":
                    buf = chart_correlation(df)
                    if buf:
                        st.image(buf, use_container_width=True)
                    else:
                        st.info("Need at least 2 numeric columns for a correlation matrix.")

        with tab_ai:
            if not _require_model():
                st.stop()
            ai_btn = st.button("Run AI Analysis", type="primary")
            if ai_btn:
                with st.spinner("IBM Granite is analysing the dataset…"):
                    try:
                        analysis = analyse_dataset(ds_file.name, df)
                        st.markdown(
                            f'<div class="report-body">{analysis}</div>',
                            unsafe_allow_html=True,
                        )
                        from src.exporter import export_txt
                        st.download_button(
                            "⬇️ Download Analysis",
                            data=export_txt(ds_file.name, analysis, []),
                            file_name=f"{ds_file.name}_analysis.txt",
                            mime="text/plain",
                        )
                    except RuntimeError as e:
                        st.error(f"❌ {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 6 – RESEARCH INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "💡 Research Insights":
    banner("Research Insights",
           "Extract findings, trends, gaps and future directions from research content")

    if not _require_model():
        st.stop()

    section("Content Source")
    source_opt = st.radio(
        "Source",
        ["Use last generated report",
         "Use last document summary",
         "Paste text manually"],
        horizontal=True,
    )

    topic_in, content_in = "", ""

    if source_opt == "Use last generated report":
        if "last_report" in st.session_state:
            topic_in = st.session_state.get("last_topic", "Research Report")
            content_in = st.session_state["last_report"]
            st.success(f"✅ Loaded: **{topic_in}**")
        else:
            st.warning("No report in session. Generate one via **Report Generator** first.")

    elif source_opt == "Use last document summary":
        if "doc_summary" in st.session_state:
            topic_in = st.session_state.get("doc_name", "Document")
            content_in = st.session_state["doc_summary"]
            st.success(f"✅ Loaded: **{topic_in}**")
        else:
            st.warning("No document summary in session. Process a document first.")

    else:
        topic_in = st.text_input("Topic label", placeholder="e.g. Quantum Computing")
        content_in = st.text_area(
            "Paste content",
            height=220,
            placeholder="Paste your research text here…",
        )

    ins_btn = st.button("Generate Insights", type="primary")

    if ins_btn:
        if not content_in.strip():
            st.warning("⚠️ Please provide content to analyse.")
        else:
            from src.research_insights import generate_insights
            with st.spinner("IBM Granite is extracting insights…"):
                try:
                    insights = generate_insights(topic_in or "Research", content_in)
                    section("Research Insights")
                    st.markdown(
                        f'<div class="report-body">{insights}</div>',
                        unsafe_allow_html=True,
                    )
                    from src.exporter import export_txt
                    st.download_button(
                        "⬇️ Download Insights",
                        data=export_txt(topic_in or "Research", insights, []),
                        file_name="research_insights.txt",
                        mime="text/plain",
                    )
                except RuntimeError as e:
                    st.error(f"❌ {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 7 – RESEARCH LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📚 Research Library":
    banner("Research Library",
           "Browse, search, view and export your saved research reports")

    from src.database import list_reports, get_report, search_reports, delete_report

    section("Search Reports")
    query = st.text_input(
        "Search",
        placeholder="Search by topic keyword…",
        label_visibility="collapsed",
    )
    reports = search_reports(query) if query.strip() else list_reports()
    st.caption(f"**{len(reports)}** report(s) found")

    if not reports:
        st.info("No reports yet. Use **Report Generator** to create your first report.")
    else:
        for r in reports:
            with st.expander(f"📋 {r['topic']}  —  {r['created_at']}"):
                col_m, col_a = st.columns([3, 1])

                with col_m:
                    st.markdown(f"**Topic:** {r['topic']}")
                    st.markdown(f"**Generated:** {r['created_at']}")
                    st.markdown(f"**Word count:** ~{r.get('word_count', 'N/A')}")
                    st.markdown(f"**Library ID:** `{r['id']}`")

                with col_a:
                    load_btn = st.button("Load", key=f"load_{r['id']}", use_container_width=True)
                    del_btn = st.button("🗑️ Delete", key=f"del_{r['id']}",
                                       use_container_width=True, type="secondary")

                if del_btn:
                    delete_report(r["id"])
                    st.success(f"Deleted: {r['topic']}")
                    st.rerun()

                if load_btn or st.session_state.get(f"loaded_{r['id']}"):
                    st.session_state[f"loaded_{r['id']}"] = True
                    full = get_report(r["id"])
                    if full:
                        st.markdown("---")
                        with st.expander("📄 Report Text"):
                            st.markdown(
                                f'<div class="report-body">{full["report_text"]}</div>',
                                unsafe_allow_html=True,
                            )

                        from src.exporter import export_txt, export_pdf
                        dl1, dl2 = st.columns(2)
                        with dl1:
                            st.download_button(
                                "⬇️ TXT",
                                data=export_txt(
                                    full["topic"], full["report_text"],
                                    full.get("sources_json", []),
                                ),
                                file_name=f"report_{r['id']}.txt",
                                mime="text/plain",
                                key=f"dtxt_{r['id']}",
                                use_container_width=True,
                            )
                        with dl2:
                            try:
                                st.download_button(
                                    "⬇️ PDF",
                                    data=export_pdf(
                                        full["topic"], full["report_text"],
                                        full.get("sources_json", []),
                                    ),
                                    file_name=f"report_{r['id']}.pdf",
                                    mime="application/pdf",
                                    key=f"dpdf_{r['id']}",
                                    use_container_width=True,
                                )
                            except RuntimeError:
                                pass


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 8 – EXPORT CENTRE
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📤 Export Centre":
    banner("Export Centre", "Download research reports as formatted PDF or TXT")

    from src.database import list_reports, get_report
    from src.exporter import export_txt, export_pdf

    reports = list_reports()
    if not reports:
        st.info("No reports in library. Generate a report first using **Report Generator**.")
        st.stop()

    section("Select Report")
    labels = [f"[{r['id']}] {r['topic']}  ({r['created_at']})" for r in reports]
    idx = st.selectbox(
        "Report",
        range(len(labels)),
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
    )
    sel = reports[idx]
    full = get_report(sel["id"])

    if not full:
        st.error("Report not found.")
        st.stop()

    card(
        f'<h3>📋 {full["topic"]}</h3>'
        f'<p style="color:#525252;font-size:13px;">'
        f'Generated: {full["created_at"]} &nbsp;|&nbsp; '
        f'~{full.get("word_count","?")} words</p>'
    )

    with st.expander("👁️ Preview Report"):
        st.markdown(
            f'<div class="report-body">{full["report_text"]}</div>',
            unsafe_allow_html=True,
        )

    section("Download Options")
    sources = full.get("sources_json", [])
    col1, col2 = st.columns(2)

    with col1:
        card("<h3>📝 Plain Text (TXT)</h3><p>Universal format — opens in any text editor or Word.</p>")
        st.download_button(
            "⬇️ Download as TXT",
            data=export_txt(full["topic"], full["report_text"], sources),
            file_name=f"report_{sel['id']}.txt",
            mime="text/plain",
            use_container_width=True,
            type="primary",
        )

    with col2:
        card("<h3>📄 PDF Document</h3><p>Professional layout with IBM styling, suitable for submission.</p>")
        try:
            st.download_button(
                "⬇️ Download as PDF",
                data=export_pdf(full["topic"], full["report_text"], sources),
                file_name=f"report_{sel['id']}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        except RuntimeError as e:
            st.warning(f"⚠️ PDF export error: {e}")

    section("Export Tips")
    st.markdown("""
- **TXT** files can be opened in Notepad, Microsoft Word, Google Docs.
- **PDF** files include IBM styling, page numbers and source references.
- All reports are stored in the SQLite database (`research_studio.db`).
    """)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 9 – SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Settings":
    banner("Settings", "Configure Ollama, Granite model and research sources")

    from src.ollama_client import get_config, set_config, get_status as _gs, OLLAMA_MODEL

    # ── Model configuration ──
    section("Granite Model Configuration")
    cfg = get_config()

    with st.form("model_form"):
        new_url = st.text_input("Ollama Base URL", value=cfg["url"])
        new_model = st.text_input("Granite Model Name", value=cfg["model"])
        submitted = st.form_submit_button("Apply Configuration")

    if submitted:
        set_config(url=new_url, model=new_model)
        _clear_status()
        st.success("✅ Configuration updated. Refreshing status…")
        st.rerun()

    # ── Connection status ──
    section("Connection Status")
    s = _gs()
    if s["ollama_online"]:
        st.success(f"✅ Ollama online at **{cfg['url']}**")
    else:
        st.error(f"❌ Ollama not reachable at **{cfg['url']}**")
        if s["error"]:
            st.code(s["error"], language=None)

    if s["model_available"]:
        st.success(f"✅ Model ready: **{s['model_name']}**")
    else:
        st.warning(f"⚠️ Model **{cfg['model']}** not found")

    if s["available_models"]:
        with st.expander("All available models"):
            for m in s["available_models"]:
                st.code(m, language=None)

    # ── Research source status ──
    section("Research Source Status")
    src_col1, src_col2, src_col3 = st.columns(3)

    def _check_url(url, timeout=5):
        try:
            r = __import__("requests").get(url, timeout=timeout)
            return r.status_code < 400
        except Exception:
            return False

    with src_col1:
        ok = _check_url("https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch=test&srlimit=1")
        st.success("✅ Wikipedia API") if ok else st.error("❌ Wikipedia API")

    with src_col2:
        ok = _check_url("https://api.openalex.org/works?search=test&per-page=1")
        st.success("✅ OpenAlex API") if ok else st.error("❌ OpenAlex API")

    with src_col3:
        ok = _check_url("https://api.crossref.org/works?query=test&rows=1")
        st.success("✅ Crossref API") if ok else st.error("❌ Crossref API")

    # ── Environment configuration guide ──
    section("Environment Configuration")
    st.markdown("""
Your `.env` file (project root) controls default settings.
**Never commit `.env` to GitHub.**

```
# .env – example settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=granite4.2:3b
OPENALEX_EMAIL=your@email.com   # optional – for higher OpenAlex rate limits
```

No paid API keys are required. All three research sources are free public APIs.
    """)

    # ── Database info ──
    section("Database")
    from src.database import _DB_PATH, get_stats
    stats = get_stats()
    st.info(
        f"📁 SQLite database: `{_DB_PATH}`  |  "
        f"{stats['total_reports']} reports  |  "
        f"{stats['total_documents']} documents"
    )

    # ── About ──
    section("About")
    st.markdown("""
| Component | Version |
|---|---|
| Application | IBM Granite Research Studio v2.0 |
| AI Model | IBM Granite 4.2 (via Ollama) |
| Research Sources | Wikipedia · OpenAlex · Crossref |
| PDF Export | ReportLab |
| Database | SQLite |
    """)
