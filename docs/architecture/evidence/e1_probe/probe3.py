import sys, pathlib, unicodedata, pypdfium2, pdfplumber
from bidi import get_display
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
GT = "التقرير السنوي ٢٠٢٥: ارتفعت المبيعات بنسبة ١٢٫٥٪ إلى 3.4 مليون ريال. مُحَمَّدٌ رسولُ الله. AgenticDoc v2"
def norm(t): return " ".join(t.split())
def lev(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1): cur.append(min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
cer=lambda h: lev(norm(h),GT)/len(GT)
out=pathlib.Path(sys.argv[1])
for name in ["pymupdf_segoeui.ttf.pdf","pymupdf_arial.ttf.pdf","edge.pdf"]:
    p=out/name
    t1=pypdfium2.PdfDocument(str(p))[0].get_textpage().get_text_range()
    with pdfplumber.open(p) as q: t2=q.pages[0].extract_text() or ""
    for lab,t in [("pypdfium2",t1),("pdfplumber",t2)]:
        lines=t.splitlines()
        rb=" ".join(get_display(l, base_dir="R") for l in lines)
        rbf=unicodedata.normalize("NFKC",rb)
        print(f"{name:<24} {lab:<10} raw={cer(t):.3f} bidi_reorder={cer(rb):.3f} bidi+NFKC={cer(rbf):.3f}")
