"""Feasibility probe (scratch, not project code): can PyMuPDF generate shaped Arabic PDFs,
and what do 4 extractors return for them?"""
import sys, unicodedata, pathlib
import pymupdf, pypdfium2, pdfplumber, pypdf

out = pathlib.Path(sys.argv[1])
font = sys.argv[2]
GT = "التقرير السنوي ٢٠٢٥: ارتفعت المبيعات بنسبة ١٢٫٥٪ إلى 3.4 مليون ريال. مُحَمَّدٌ رسولُ الله. AgenticDoc v2"

doc = pymupdf.open()
page = doc.new_page()
css = f"@font-face {{font-family: ar; src: url({pathlib.Path(font).name});}} body {{font-family: ar; font-size: 14px;}}"
arch = pymupdf.Archive(str(pathlib.Path(font).parent))
html = f'<div dir="rtl" lang="ar">{GT}</div>'
rc = page.insert_htmlbox(pymupdf.Rect(40, 40, 560, 300), html, css=css, archive=arch)
print("insert_htmlbox rc:", rc)
doc.save(out)

def pf_counts(t):
    return sum(1 for c in t if 0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF)

def show(name, t):
    t = " ".join(t.split())
    print(f"--- {name}: len={len(t)} presentation_forms={pf_counts(t)} equal_GT={t == GT} equal_GT_NFKC={unicodedata.normalize('NFKC', t) == GT}")
    print("   ", t[:160])

d = pymupdf.open(out)
show("pymupdf text", d[0].get_text("text"))
show("pymupdf text sort", d[0].get_text("text", sort=True))
pdf = pypdfium2.PdfDocument(str(out))
show("pypdfium2", pdf[0].get_textpage().get_text_range())
with pdfplumber.open(out) as p:
    show("pdfplumber", p.pages[0].extract_text() or "")
show("pypdf", pypdf.PdfReader(out).pages[0].extract_text())
print("GT  :", GT)
