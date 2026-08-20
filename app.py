"""Streamlit interface for the bank statement document extractor."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile

import streamlit as st

from config.settings import ensure_runtime_directories, load_settings
from src.ingestion.pdf_reader import PdfReaderError, read_pdf_text
from src.orchestration.merge import merge_parallel_results
from src.orchestration.parallel_runner import run_parallel_extraction
from src.orchestration.reflection import run_reflection_if_needed
from src.validation.validator import validate_merged_statement

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


st.set_page_config(
    page_title="Bank Statement Extractor",
    page_icon="▦",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #f7f4ed; }
    [data-testid="stHeader"] { background: rgba(247, 244, 237, 0.9); }
    .hero { padding: 1.3rem 0 1rem; border-bottom: 1px solid #d9d4c8; }
    .hero h1 { color: #153f45; font-family: Georgia, serif; font-size: 2.8rem; margin: 0; }
    .hero p { color: #5d6b76; font-size: 1.05rem; }
    .stage { padding: .75rem 1rem; border-left: 4px solid #0b6b68; background: #d8eeea; margin: .45rem 0; }
    .warning-box { padding: 1rem; border-left: 4px solid #c75b42; background: #fff0e9; }
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


def main() -> None:
    settings = load_settings()
    ensure_runtime_directories(settings)

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

    try:
        with tempfile.TemporaryDirectory(dir=settings.input_directory) as upload_directory:
            pdf_path = _save_uploaded_pdf(uploaded_file, Path(upload_directory))
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
            _show_result(merged_statement, validation_result, reflection_result)
    except PdfReaderError as error:
        st.error(str(error))
    except Exception:
        st.error("The application could not complete this run. Check your provider settings and try again.")


if __name__ == "__main__":
    main()
