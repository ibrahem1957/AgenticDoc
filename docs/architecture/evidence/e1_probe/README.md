# E1 feasibility probe (2026-11-16)

Scratch research by Claude, **not production code and not a benchmark**: a single Arabic/English sentence. Summary and design consequences are in `../../EXTRACTION_LAB_DESIGN.md` §7.

Environment: Windows 11, Python 3.12.10, PyMuPDF 2.1, pypdfium2 5.15.2, pdfplumber 0.11.10 (pdfminer.six 20260107), pypdf 7.1.0, python-bidi (latest on 2026-11-16), Microsoft Edge headless; fonts from `C:\Windows\Fonts`.

- `probe_arabic.py <out.pdf> <font.ttf>`: first probe (single font).
- `probe2.py <out_dir>`: 4 fonts with PyMuPDF `insert_htmlbox` + Edge `--print-to-pdf`, 4 extractors → `probe2_output.txt`.
- `probe3.py <out_dir_of_probe2>`: effect of bidi reordering and NFKC on pypdfium2/pdfplumber → `probe3_output.txt`.

Run in an isolated venv: `python -I -X utf8 probe2.py out/`.
