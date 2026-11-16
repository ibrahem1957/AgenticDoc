from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated"
FONT_PATH = ROOT / "fonts" / "Amiri-Regular.ttf"


@dataclass(frozen=True)
class Fixture:
    name: str
    pages: list[str]
    tags: list[list[str]]
    columns: int = 1
    image_only: bool = False
    heading: bool = False
    header_footer: bool = False


def _arabic_digits(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


FIXTURES = [
    Fixture(
        "en_single_column",
        ["AgenticDoc extraction lab.\nThis is a deterministic English paragraph."],
        [[]],
    ),
    Fixture(
        "ar_single_column",
        ["مختبر استخراج المستندات\nهذه فقرة عربية واضحة لاختبار ترتيب النص."],
        [["headings"]],
        heading=True,
    ),
    Fixture("ar_diacritics", ["مُحَمَّدٌ يَقْرَأُ النَّصَّ العَرَبِيَّ بِدِقَّةٍ."], [["diacritics"]]),
    Fixture(
        "mixed_numbers",
        ["تقرير ٢٠٢٥ — Revenue 2025\nالقيمة ١٢٫٥٪ والسعر ٣٠ ريال — Total: 30 SAR."],
        [["mixed_ar_en", "arabic_indic_digits", "western_digits"]],
    ),
    Fixture(
        "ar_two_column",
        [
            "العمود الأيمن\nالنص الأول في الصفحة.\n\nالعمود الأيسر\nالنص الثاني في الصفحة."
        ],
        [["multi_column", "headings"]],
        columns=2,
        heading=True,
    ),
    Fixture(
        "header_footer",
        [
            f"تقرير تجريبي\n\nمحتوى الصفحة رقم {_arabic_digits(number)}\n\n— {_arabic_digits(number)} —"
            for number in range(1, 4)
        ],
        [["header_footer", "arabic_indic_digits"] for _ in range(3)],
        header_footer=True,
    ),
    Fixture(
        "multi_page",
        [
            f"الفصل {number}\nهذا محتوى اصطناعي للصفحة {number}."
            for number in range(1, 6)
        ],
        [["headings"] for _ in range(5)],
        heading=True,
    ),
    Fixture(
        "image_only", ["صورة نصية بلا طبقة نص"], [["images_present"]], image_only=True
    ),
]


def _require_font() -> None:
    if not FONT_PATH.is_file():
        raise RuntimeError(f"Missing redistributable Arabic font: {FONT_PATH}")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _section_html(text: str, heading: bool) -> str:
    lines = text.splitlines()
    if heading and lines:
        first, *rest = lines
        tail = "<br>".join(_escape(line) for line in rest)
        return f"<h1>{_escape(first)}</h1>{tail}"
    return "<br>".join(_escape(line) for line in lines)


def _html(text: str, columns: int, heading: bool = False) -> str:
    if columns == 2:
        parts = text.split("\n\n", 1)
        cells = "".join(
            f'<div class="col">{_section_html(part, heading)}</div>' for part in parts
        )
        return f'<div class="cols">{cells}</div>'
    return f'<div class="body">{_section_html(text, heading)}</div>'


def _page_html(fixture: Fixture, text: str) -> str:
    if fixture.header_footer:
        header, body, footer = text.split("\n\n", 2)
        return (
            f'<div class="running-header">{_escape(header)}</div>'
            f'<div class="page-body">{_escape(body)}</div>'
            f'<div class="running-footer">{_escape(footer)}</div>'
        )
    return _html(text, fixture.columns, fixture.heading)


def _create_pdf(fixture: Fixture, target: Path) -> None:
    document = pymupdf.open()
    archive = pymupdf.Archive(str(FONT_PATH.parent))
    css = (
        "@font-face {font-family: Amiri; src: url(Amiri-Regular.ttf);}"
        "* {font-family: Amiri; font-size: 18pt;} .body {direction: rtl; text-align: right;}"
        ".cols {display:flex; flex-direction:row-reverse; gap:30pt;} .col {width:48%; direction:rtl; text-align:right;}"
        "h1 {font-size:26pt;font-weight:bold;margin:0 0 14pt 0;}"
        ".running-header,.running-footer,.page-body {direction:rtl;text-align:center;}"
    )
    for text in fixture.pages:
        page = document.new_page(width=595, height=842)
        if fixture.image_only:
            temporary = pymupdf.open()
            source_page = temporary.new_page(width=500, height=180)
            source_page.insert_htmlbox(
                pymupdf.Rect(20, 20, 480, 160), _html(text, 1), css=css, archive=archive
            )
            pixmap = source_page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            page.insert_image(
                pymupdf.Rect(48, 100, 547, 280), stream=pixmap.tobytes("png")
            )
            temporary.close()
        else:
            if fixture.columns == 2:
                right, left = text.split("\n\n", 1)
                page.insert_htmlbox(
                    pymupdf.Rect(305, 90, 547, 750),
                    _html(right, 1, fixture.heading),
                    css=css,
                    archive=archive,
                )
                page.insert_htmlbox(
                    pymupdf.Rect(48, 90, 290, 750),
                    _html(left, 1, fixture.heading),
                    css=css,
                    archive=archive,
                )
            elif fixture.header_footer:
                header, body, footer = text.split("\n\n", 2)
                for rectangle, content, class_name in (
                    (pymupdf.Rect(48, 28, 547, 82), header, "running-header"),
                    (pymupdf.Rect(48, 115, 547, 720), body, "page-body"),
                    (pymupdf.Rect(48, 765, 547, 820), footer, "running-footer"),
                ):
                    page.insert_htmlbox(
                        rectangle,
                        f'<div class="{class_name}">{_escape(content)}</div>',
                        css=css,
                        archive=archive,
                    )
            else:
                page.insert_htmlbox(
                    pymupdf.Rect(48, 60, 547, 780),
                    _html(text, fixture.columns, fixture.heading),
                    css=css,
                    archive=archive,
                )
    metadata = document.metadata
    metadata.update(
        {
            "producer": "AgenticDoc fixture generator / PyMuPDF",
            "creator": "lab.fixtures.generate_fixtures",
        }
    )
    document.set_metadata(metadata)
    document.save(target, garbage=4, deflate=True)
    document.close()


def _render_first(pdf_path: Path, output_path: Path) -> None:
    document = pymupdf.open(pdf_path)
    try:
        pixmap = document[0].get_pixmap(
            matrix=pymupdf.Matrix(110 / 72, 110 / 72), alpha=False
        )
        pixmap.save(output_path)
    finally:
        document.close()


def _write_ground_truth(
    fixture: Fixture,
    directory: Path,
    producer: str,
    producer_version: str,
    filename: str,
) -> None:
    payload = {
        "schema_version": 1,
        "task": "text",
        "source": "fixture",
        "fixture": fixture.name,
        "producer": producer,
        "producer_version": producer_version,
        "font": "Amiri Regular",
        "pages": [
            {
                "page": index,
                "text": text,
                "status": "verified",
                "tags": fixture.tags[index - 1],
            }
            for index, text in enumerate(fixture.pages, start=1)
        ],
    }
    (directory / filename).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _find_chromium() -> Path | None:
    candidates = [
        shutil.which(name)
        for name in ("msedge", "chrome", "chromium", "chromium-browser")
    ] + [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _create_chromium_variant(fixture: Fixture, browser: Path, directory: Path) -> None:
    if fixture.image_only:
        return
    with tempfile.TemporaryDirectory() as temp_dir:
        html_path = Path(temp_dir) / "fixture.html"
        body = "".join(
            f'<section class="page">{_page_html(fixture, text)}</section>'
            for text in fixture.pages
        )
        html_path.write_text(
            "<meta charset='utf-8'><style>"
            "@font-face{font-family:Amiri;src:url('file:///"
            + FONT_PATH.as_posix()
            + "')} @page{size:A4;margin:0}.page{height:290mm;box-sizing:border-box;page-break-after:always;position:relative;font-family:Amiri;font-size:18pt;padding:25mm 18mm}.page:last-child{page-break-after:auto}"
            ".body{direction:rtl;text-align:right}.cols{display:flex;flex-direction:row-reverse;gap:30px}.col{width:48%;direction:rtl;text-align:right}"
            "h1{font-size:26pt;font-weight:bold;margin:0 0 14pt 0}.running-header{position:absolute;top:10mm;left:18mm;right:18mm;text-align:center;direction:rtl}"
            ".page-body{position:absolute;top:42mm;left:18mm;right:18mm;text-align:center;direction:rtl}.running-footer{position:absolute;bottom:10mm;left:18mm;right:18mm;text-align:center;direction:rtl}"
            "</style>" + body,
            encoding="utf-8",
        )
        pdf_path = directory / "document_chromium.pdf"
        completed = subprocess.run(
            [
                str(browser),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode == 0 and pdf_path.is_file():
            _render_first(pdf_path, directory / "page1_chromium.png")
            _write_ground_truth(
                fixture,
                directory,
                "Chromium",
                browser.name,
                "ground_truth_chromium.json",
            )
        else:
            print(
                f"NOTICE: Chromium variant skipped for {fixture.name}: exit {completed.returncode}"
            )


def _create_png() -> None:
    target = OUTPUT / "standalone_png"
    target.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    page = document.new_page(width=600, height=240)
    archive = pymupdf.Archive(str(FONT_PATH.parent))
    page.insert_htmlbox(
        pymupdf.Rect(20, 20, 580, 220),
        _html("صورة PNG اصطناعية — Synthetic image", 1),
        css="@font-face {font-family: Amiri; src: url(Amiri-Regular.ttf);} * {font-family:Amiri;font-size:22pt}",
        archive=archive,
    )
    pixmap = page.get_pixmap(alpha=False)
    pixmap.save(target / "image.png")
    document.close()
    (target / "ground_truth.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "fixture",
                "pages": [
                    {
                        "page": 1,
                        "text": "صورة PNG اصطناعية — Synthetic image",
                        "status": "verified",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    _require_font()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    browser = _find_chromium()
    for fixture in FIXTURES:
        directory = OUTPUT / fixture.name
        directory.mkdir(parents=True, exist_ok=True)
        pdf_path = directory / "document_pymupdf.pdf"
        _create_pdf(fixture, pdf_path)
        _render_first(pdf_path, directory / "page1_pymupdf.png")
        _write_ground_truth(
            fixture,
            directory,
            "PyMuPDF",
            pymupdf.__doc__.split()[1] if pymupdf.__doc__ else "unknown",
            "ground_truth_pymupdf.json",
        )
        if browser:
            _create_chromium_variant(fixture, browser, directory)
    _create_png()
    print(f"Generated synthetic fixtures at {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
