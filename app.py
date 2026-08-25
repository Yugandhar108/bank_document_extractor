"""Streamlit interface for the bank statement document extractor."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import tempfile

import streamlit as st
import streamlit.components.v1 as components

from config.settings import ensure_runtime_directories, load_settings
from src.agents.base_agent import AgentCallError
from src.ingestion.pdf_reader import PdfReaderError, read_pdf_text
from src.logging_utils import get_app_logger, log_event, new_run_id, reset_run_id, set_run_id
from src.orchestration.merge import merge_parallel_results
from src.orchestration.parallel_runner import run_parallel_extraction
from src.orchestration.reflection import run_reflection_if_needed
from src.validation.validator import validate_merged_statement

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
WIKI_FILE = Path(__file__).with_name("WIKI.html")


st.set_page_config(
    page_title="Bank Statement Extractor",
    page_icon="▦",
    layout="wide",
)

st.markdown(
    """
    <style>
        :root {
            --app-bg: #f2f6fb;
            --surface: #ffffff;
            --sidebar: #eaf2fb;
            --ink: #102a43;
            --muted: #48647e;
            --border: #c5d7eb;
            --primary: #0067b1;
            --primary-hover: #004f89;
            --navy: #003f77;
            --accent: #f58220;
            --success-bg: #e2f2e8;
            --success-ink: #185a37;
            --warning-bg: #fff3d6;
            --warning-ink: #73510c;
            --error-bg: #fae5e5;
            --error-ink: #8a2020;
        }
        .stApp { background: var(--app-bg); color: var(--ink); }
        [data-testid="stHeader"] { background: rgba(244, 247, 251, .98); border-bottom: 1px solid var(--border); }
        [data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid var(--border); }
        [data-testid="stSidebar"] * { color: var(--ink); }
        .hero { padding: 1.4rem 1.5rem 1.2rem; background: var(--navy); border-radius: 4px; border-bottom: 4px solid var(--accent); }
        .hero h1 { color: #ffffff; font-family: Georgia, serif; font-size: 2.5rem; margin: 0; }
        .hero p { color: #d8e5f5; font-size: 1.02rem; font-weight: 500; }
        .stage { padding: .85rem 1rem; border: 1px solid #b6d1ea; border-left: 5px solid var(--primary); border-radius: 3px; background: #e8f3fd; color: #103d68; font-weight: 600; margin: .55rem 0; }
        [data-testid="stFileUploaderDropzone"], [data-testid="stTextArea"] textarea { background: var(--surface); border-color: #8bb7df; color: var(--ink); }
        [data-testid="stFileUploaderDropzone"] * { color: var(--ink); }
        [data-testid="stFileUploader"] button {
            background: var(--primary);
            border: 1px solid var(--primary);
            color: #ffffff;
            font-weight: 700;
            min-height: 2.7rem;
        }
        [data-testid="stFileUploader"] button:hover,
        [data-testid="stFileUploader"] button:focus {
            background: var(--primary-hover);
            border-color: var(--primary-hover);
            color: #ffffff;
        }
        .stButton > button { background: var(--primary); border: 1px solid var(--primary); color: #ffffff; font-weight: 700; min-height: 2.7rem; }
        .stButton > button:hover, .stButton > button:focus { background: var(--primary-hover); border-color: var(--primary-hover); color: #ffffff; }
        [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--border); border-radius: 3px; padding: .7rem; }
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: var(--ink); }
        [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 3px; overflow: hidden; }
        [data-testid="stAlert"] { color: var(--ink); border-radius: 3px; }
        [data-testid="stAlert"][data-baseweb="notification"] { border: 1px solid var(--border); }
        .stSuccess { background: var(--success-bg); color: var(--success-ink); }
        .stWarning { background: var(--warning-bg); color: var(--warning-ink); }
        .stError { background: var(--error-bg); color: var(--error-ink); }
        .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted); }
        h2, h3, p, label, summary { color: var(--ink); }
    </style>
    <div class="hero">
      <h1>Bank Statement Extractor</h1>
      <p>Upload a statement, let three focused AI workers read it, then review the checks and extracted transactions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def _save_uploaded_pdf(uploaded_file, input_directory: Path) -> Path:
    """Save an upload using only its filename, inside the configured input folder."""
    safe_name = Path(uploaded_file.name).name
    if not safe_name.lower().endswith(".pdf"):
        raise ValueError("Please upload a PDF file.")
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Please upload a PDF smaller than 25 MB.")

    input_directory.mkdir(parents=True, exist_ok=True)
    target = input_directory / safe_name
    target.write_bytes(uploaded_file.getbuffer())
    return target


def _show_agent_timings(parallel_result) -> None:
    timing_rows = [
        {
            "Agent": timing.agent_name.replace("_", " ").title(),
            "Started": timing.started_at,
            "Ended": timing.ended_at,
            "Duration (seconds)": timing.duration_seconds,
        }
        for timing in parallel_result.timings
    ]
    st.dataframe(timing_rows, use_container_width=True, hide_index=True)


def _show_result(merged_statement, validation_result, reflection_result) -> None:
    st.subheader("Extracted account details")
    account_columns = st.columns(4)
    account_fields = [
        ("Customer", merged_statement.customer_name),
        ("Bank", merged_statement.bank_name),
        ("Account number", merged_statement.account_number),
        ("Statement period", f"{merged_statement.statement_start_date} to {merged_statement.statement_end_date}"),
    ]
    for column, (label, value) in zip(account_columns, account_fields):
        column.metric(label, value or "Not found")

    st.subheader("Transactions")
    transaction_rows = [row.model_dump() for row in merged_statement.transactions]
    if transaction_rows:
        st.dataframe(transaction_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions were extracted.")

    st.subheader("Validation")
    if validation_result.is_valid:
        st.success("All validation checks passed.")
    else:
        st.error(f"Validation found {len(validation_result.errors)} issue(s).")
        st.dataframe(
            [error.model_dump() for error in validation_result.errors],
            use_container_width=True,
            hide_index=True,
        )

    if merged_statement.merge_conflicts:
        st.subheader("Merge conflicts")
        st.dataframe(
            [conflict.model_dump() for conflict in merged_statement.merge_conflicts],
            use_container_width=True,
            hide_index=True,
        )

    if reflection_result:
        st.subheader("Reflection")
        st.warning(reflection_result.mistake_description)
        st.write("Correction rule:", reflection_result.correction_rule)
        st.write(f"Confidence: {reflection_result.confidence:.0%}")

    with st.expander("Prompt versions used"):
        st.json(merged_statement.prompt_versions)


def _show_project_wiki() -> None:
    """Render the project guide inside a dedicated application tab."""
    st.subheader("Project Wiki")
    st.caption("Project guide, setup steps, architecture, security, and troubleshooting.")
    if not WIKI_FILE.is_file():
        st.error("The project wiki file could not be found.")
        return
    wiki_html = WIKI_FILE.read_text(encoding="utf-8")
    navigation_script = """
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            document.querySelectorAll('a[href^="#"]').forEach((link) => {
                link.addEventListener("click", (event) => {
                    event.preventDefault();
                    const section = document.getElementById(link.getAttribute("href").slice(1));
                    if (section) {
                        section.scrollIntoView({ behavior: "smooth", block: "start" });
                    }
                });
            });
        });
    </script>
    """
    embedded_wiki = wiki_html.replace("</body>", f"{navigation_script}</body>")
    components.html(embedded_wiki, height=900, scrolling=True)


def main() -> None:
    settings = load_settings()
    ensure_runtime_directories(settings)
    startup_logger = get_app_logger(settings.log_directory)
    log_event(
        startup_logger,
        logging.INFO,
        "Model selected",
        provider=settings.provider or "none",
        model=settings.model or "none",
        model_source=settings.model_source,
    )

    extractor_tab, wiki_tab = st.tabs(["Extractor", "Project Wiki"])

    with wiki_tab:
        _show_project_wiki()

    with extractor_tab:
        with st.sidebar:
            st.header("Process a document")
            uploaded_file = st.file_uploader("Choose a bank statement PDF", type=["pdf"])
            memory_context = st.text_area(
                "Memory context",
                value="",
                help="Optional source-specific guidance to include in the extraction prompts.",
            )
            run_button = st.button("Run extraction", type="primary", use_container_width=True)
            st.caption(f"Provider: {settings.provider.title() or 'Not configured'}")
            st.caption(f"Model: {settings.model or 'Not configured'}")
            st.caption(f"Selection: {settings.model_source}")
            st.caption("Privacy: document text is sent to the selected AI provider.")

        if not run_button:
            st.info("Upload a PDF in the sidebar, then select Run extraction.")
            return
        if not uploaded_file:
            st.warning("Please upload a PDF before starting.")
            return
        if not settings.is_configured:
            st.error(settings.configuration_message)
            return

        progress = st.progress(0)
        status = st.empty()
        run_id = new_run_id()
        logger = get_app_logger(settings.log_directory)
        run_token = set_run_id(run_id)
        st.caption(f"Run ID: {run_id}")

        try:
            log_event(logger, logging.INFO, "Run started", provider=settings.provider, model=settings.model)
            with tempfile.TemporaryDirectory(dir=settings.input_directory) as upload_directory:
                pdf_path = _save_uploaded_pdf(uploaded_file, Path(upload_directory))
                log_event(logger, logging.INFO, "PDF accepted", file_size_bytes=uploaded_file.size)
                status.markdown('<div class="stage">1. Reading the PDF...</div>', unsafe_allow_html=True)
                document_text = read_pdf_text(pdf_path, Path(upload_directory))
                if not document_text.strip():
                    st.error("This PDF has no embedded text. It may be a scanned document.")
                    return
                progress.progress(20)

                status.markdown('<div class="stage">2. Running three extraction workers in parallel...</div>', unsafe_allow_html=True)
                parallel_result = asyncio.run(
                    run_parallel_extraction(
                        document_text=document_text,
                        memory_context=memory_context,
                        settings=settings,
                    )
                )
                progress.progress(60)
                with st.expander("Parallel worker timing evidence", expanded=True):
                    _show_agent_timings(parallel_result)

                status.markdown('<div class="stage">3. Combining worker results...</div>', unsafe_allow_html=True)
                merged_statement = merge_parallel_results(parallel_result)
                progress.progress(75)

                status.markdown('<div class="stage">4. Checking the extracted information...</div>', unsafe_allow_html=True)
                validation_result = validate_merged_statement(merged_statement)
                progress.progress(85)

                reflection_result = None
                if not validation_result.is_valid:
                    status.markdown('<div class="stage">5. Explaining the validation problem...</div>', unsafe_allow_html=True)
                    reflection_result, _ = run_reflection_if_needed(
                        validation_result=validation_result,
                        merged_statement=merged_statement,
                        document_text=document_text,
                    )
                else:
                    status.markdown('<div class="stage">5. Validation passed. No reflection was needed.</div>', unsafe_allow_html=True)
                progress.progress(100)
                status.success("Processing complete.")
                log_event(logger, logging.INFO, "Run completed", validation_passed=validation_result.is_valid)
                _show_result(merged_statement, validation_result, reflection_result)
        except AgentCallError as error:
            log_event(logger, logging.ERROR, "Run failed during provider call", error_type=type(error).__name__)
            st.error(f"{error} (Run ID: {run_id})")
        except PdfReaderError as error:
            log_event(logger, logging.ERROR, "Run failed while reading PDF", error_type=type(error).__name__)
            st.error(str(error))
        except Exception:
            log_event(logger, logging.ERROR, "Run failed unexpectedly", error_type="UnexpectedError")
            st.error(f"The application could not complete this run. Check logs/application.log using Run ID {run_id}.")
        finally:
            reset_run_id(run_token)


if __name__ == "__main__":
    main()
