"""Scratch probe 2: font dependence of PyMuPDF fixtures + Edge (Chromium) as a second producer."""
import sys, unicodedata, pathlib, subprocess, shutil
import pymupdf, pypdfium2, pdfplumber, pypdf

GT = "التقرير السنوي ٢٠٢٥: ارتفعت المبيعات بنسبة ١٢٫٥٪ إلى 3.4 مليون ريال. مُحَمَّدٌ رسولُ الله. AgenticDoc v2"
out = pathlib.Path(sys.argv[1]); out.mkdir(exist_ok=True)

def pf(t): return sum(1 for c in t if 0xFB50 <= ord(c) <= 0xFDFF or 0xFE70 <= ord(c) <= 0xFEFF)
def norm(t): return " ".join(t.split())
def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
def cer(h): return lev(norm(h), GT) / len(GT)

def extract_all(p):
    d = pymupdf.open(p)
    r = {"pymupdf": d[0].get_text("text"),
         "pypdfium2": pypdfium2.PdfDocument(str(p))[0].get_textpage().get_text_range(),
         "pypdf": pypdf.PdfReader(p).pages[0].extract_text()}
    with pdfplumber.open(p) as q:
        r["pdfplumber"] = q.pages[0].extract_text() or ""
    return r

def report(label, p):
    print(f"=== producer: {label}")
    for k, t in extract_all(p).items():
        f = unicodedata.normalize("NFKC", norm(t))
        print(f"  {k:<10} CER={cer(t):.3f} CER_after_NFKC={cer(f):.3f} pres_forms={pf(t)} | {norm(t)[:110]}")

for font in ["arial.ttf", "tahoma.ttf", "times.ttf", "segoeui.ttf"]:
    src = pathlib.Path("C:/Windows/Fonts") / font
    if not src.exists(): continue
    doc = pymupdf.open(); page = doc.new_page()
    arch = pymupdf.Archive("C:/Windows/Fonts")
    css = f"@font-face {{font-family: ar; src: url({font});}} body {{font-family: ar; font-size: 14px;}}"
    page.insert_htmlbox(pymupdf.Rect(40, 40, 560, 300), f'<div dir="rtl" lang="ar">{GT}</div>', css=css, archive=arch)
    p = out / f"pymupdf_{font}.pdf"; doc.save(p)
    report(f"pymupdf insert_htmlbox / {font}", p)

edge = next((x for x in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if pathlib.Path(x).exists()), None)
if edge:
    html = out / "ar.html"
    html.write_text(f'<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><body style="font-family:Arial;font-size:14px">{GT}</body></html>', encoding="utf-8")
    p = out / "edge.pdf"
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={p}", html.as_uri()],
                   capture_output=True, timeout=90)
    if p.exists(): report("Edge headless print-to-pdf / Arial", p)
    else: print("edge produced no pdf")
else:
    print("no edge")
print("GT:", GT)
