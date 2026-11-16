# AgenticDoc Extraction Lab — E1-A

The Extraction Lab is a local Streamlit tool for comparing the raw text produced by PyMuPDF, pypdfium2, pdfplumber, and pypdf against the rendered PDF page. It is independent of `src/` and does not change the existing RAG application.

E1-A evaluates native PDF text layers only. It is not OCR and does not select a production extractor. A user must manually upload and inspect a PDF before E1-A can be accepted; automated tests alone are insufficient.

## Windows PowerShell setup

Open PowerShell and run:

```powershell
cd "C:\Users\User\Downloads\chat\Project sdaia"

py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r .\lab\requirements-lab.txt
```

The verified Windows runtime is Python 3.12 x64. If `py -3.12` is unavailable, install Python 3.12 and recreate the environment; Python 3.11 and 3.13 have not yet been verified for this checkpoint.

```powershell
python -m venv .venv
```

## Launch Streamlit on Windows

With the virtual environment activated and PowerShell still inside `Project sdaia`:

```powershell
python -m lab.launch
```

**Always launch through `lab.launch`.** Don't use `streamlit run` directly. Streamlit reads `.streamlit/config.toml` only from the current directory, so started from `Project sdaia` it ignores `lab/.streamlit/config.toml`. It then binds to **all network interfaces** (other machines on the LAN can reach the lab and its uploaded documents), queries an internet service for the machine's external IP, and enables browser usage statistics. `lab.launch` always passes `--server.address 127.0.0.1` and `--browser.gatherUsageStats false`, and refuses to override them. Extra Streamlit options can still be passed, e.g. `python -m lab.launch --server.port 8502`.

Open the local URL shown in PowerShell, normally `http://127.0.0.1:8501`.

### Windows application-control note

The lab's document details and extraction results use Streamlit text/image primitives and do not require Pandas. Pandas remains a transitive Streamlit dependency, but the E1-A pages deliberately avoid dataframe-capable display calls because some managed Windows environments block unsigned NumPy extension modules under WDAC or an equivalent enterprise policy.

If Windows reports `Application Control policy has blocked this file`, inspect the **Microsoft-Windows-CodeIntegrity/Operational** log and record the blocked path and policy ID. Do not disable Defender, Smart App Control, WDAC, AppLocker, or another security control, and do not assume reinstalling NumPy will change an enterprise signing decision.

## Manual extraction comparison

1. Open **Documents** in the Streamlit sidebar.
2. Upload a PDF. The file stays in a temporary workspace and is never committed automatically.
3. Verify that the original page renders. For Arabic, verify shaping, RTL direction, diacritics, and Arabic/Western numerals visually.
4. Open **Run Text Extraction**, select the PDF and pages, and run all four local extractors. Enable **Re-run (bypass cache)** when you need a fresh execution.
5. Open **Compare**. Confirm that the original page is visible beside every extractor's **RAW — exactly as extracted** text.
6. Toggle the block-order overlay and invisible-character markers. Confirm that Arabic text is readable and that each result corresponds to the same selected page.
7. Record any mismatch or startup/rendering problem in the E1-A review; do not mark E1-A complete until this walkthrough succeeds.

## Temporary data and privacy

- Uploaded documents, page PNGs, and extracted text are stored beneath `%TEMP%\agenticdoc-lab\ws_*` by default.
- **Never commit or push user PDFs, images, extracted text, or workspace directories.** Only synthetic fixtures under the project may be committed.
- Ending a workspace deletes its local directory. Abandoned workspaces are deleted after the configured TTL (24 hours by default).
- E1 has no API adapters and makes no external calls. All E1-A extraction runs stay local.
- The application does not log extracted document text.

## Generate synthetic fixtures and run the headless bench

```powershell
python -m lab.fixtures.generate_fixtures
python -m lab.core.bench --fixtures .\lab\fixtures\generated --out .\lab_exports\e1_fixture_bench
```

Generated fixtures and bench output are ignored by Git. They contain synthetic content only.
The bench reports text-extraction time separately from adapter startup and optional block-overlay generation; do not add those columns together or interpret this synthetic bench as an extractor selection.

## Run E1-A checks

```powershell
python -m ruff check .\lab .\tests\lab
python -m pytest .\tests\lab --cov=lab.core --cov-report=term-missing
```

## Adding an adapter

E1-A adapters implement the protocol in `lab/core/adapters/base.py`. Add one module with `create_adapter(info)` and one entry in `lab/config/adapters.toml`. Do not add OCR, vision, table, or chart adapters during E1-A.

