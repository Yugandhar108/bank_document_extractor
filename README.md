# Bank Statement Document Extractor

This project turns a messy bank statement PDF into organized information.
It can find account details, customer details, balances, and transactions, then
check whether the extracted numbers make sense.

The project uses several small AI workers instead of one large request. This makes
the work easier to understand, test, and improve.

## In simple words

The system:

1. Reads a bank statement PDF safely.
2. Sends different parts of the work to three small AI workers.
3. Combines their answers into one result.
4. Checks dates, required fields, and balance calculations.
5. Explains the likely cause when a check fails.

## Application features

- Safe PDF text extraction from every page.
- Protection against reading files outside `data/input`.
- Three extraction agents:
  - account metadata
  - customer identity
  - transaction table
- Parallel execution with start and end timestamps.
- Deterministic merge with conflict reporting.
- Direct preservation of the transaction table during merge.
- Rule-based validation of fields, dates, amounts, and balances.
- Conditional reflection when validation fails.
- Versioned prompt files.
- Streamlit interface with live processing stages.
- Transaction table, validation errors, conflicts, timing, and reflection display.
- Automated tests for the implemented behavior.

## Project structure

- `config` - Settings and model pricing.
- `data/input` - PDF files to process.
- `data/output` - Output files created by the application.
- `prompts` - Versioned instructions for AI workers.
- `src/ingestion` - Safe PDF reading.
- `src/agents` - Individual extraction and reflection agents.
- `src/models` - Structured data models.
- `src/orchestration` - Parallel execution, merging, and reflection flow.
- `src/validation` - Mechanical checks for extracted data.
- `src/memory` - Memory-related application components.
- `src/telemetry` - Usage and cost tracking components.
- `src/hitl` - Human review components.
- `storage` - Local persistent data.
- `tests` - Automated tests.

## Setup

From this project folder, install the packages:

```powershell
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.venv/.env`, then add one private provider key. The
application checks all supported provider settings and uses the selected provider
when it has a real key. If no provider is selected, it uses the first available
real key. Placeholder values are ignored.

Supported keys are `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`,
`OPENROUTER_API_KEY`, and `HUGGINGFACE_API_KEY`. Never put a real key in
`.env.example` or commit `.venv/.env` to source control.

## Tests

Run all automated tests with:

```powershell
python -m pytest -q
```

The tests use mocked AI responses, so they do not require a live API request.

## Notes

- A scanned PDF without an embedded text layer returns no text. OCR is not added yet.
- Provider free-tier limits and model prices can change.
- If an API key has been shared publicly, revoke it and create a replacement.
- Upload only documents that your organization permits sending to an AI provider.

## Security protections

- Provider secrets are loaded from `.venv/.env` and are never shown in the UI.
- `.venv/.env` is excluded from Git.
- Placeholder keys are ignored.
- Custom provider endpoints must use HTTPS and cannot contain credentials.
- PDF paths are resolved and restricted to the allowed input directory.
- PDF files are limited to 25 MB to reduce resource-exhaustion risk.
- Uploaded files use a sanitized name, temporary storage, and automatic cleanup.
- Unexpected processing errors show a general message rather than raw exception text.
- Document text is marked as untrusted data in prompts to reduce prompt-injection risk.

## Start the application

Run Streamlit from the project folder:

```powershell
python -m streamlit run app.py
```

The browser page lets you upload a PDF, start extraction, see each processing
stage, review the transaction table, and inspect validation or reflection output.
Uploaded PDFs are stored temporarily and removed when processing ends.
Document text is sent to the selected AI provider for processing.

## More information

Open [WIKI.html](WIKI.html) for a visual guide written for both non-technical and
technical readers.
