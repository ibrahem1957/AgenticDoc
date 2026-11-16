from __future__ import annotations

from pathlib import Path

import pymupdf

from lab.fixtures.generate_fixtures import FIXTURES, _create_pdf, _page_html


def _fixture(name: str):
    return next(item for item in FIXTURES if item.name == name)


def _text_blocks(path: Path) -> list[tuple]:
    document = pymupdf.open(path)
    try:
        return [block for block in document[0].get_text("blocks") if block[6] == 0]
    finally:
        document.close()


def test_pymupdf_two_column_fixture_uses_side_by_side_rectangles(
    tmp_path: Path,
) -> None:
    target = tmp_path / "two-column.pdf"
    _create_pdf(_fixture("ar_two_column"), target)
    blocks = _text_blocks(target)
    assert any(float(block[0]) >= 300 for block in blocks)
    assert any(float(block[2]) <= 300 for block in blocks)


def test_header_footer_fixture_uses_margins_and_arabic_indic_page_number(
    tmp_path: Path,
) -> None:
    fixture = _fixture("header_footer")
    target = tmp_path / "header-footer.pdf"
    _create_pdf(fixture, target)
    blocks = _text_blocks(target)
    assert any(float(block[1]) < 90 for block in blocks)
    assert any(float(block[3]) > 760 for block in blocks)
    assert "— ١ —" in fixture.pages[0]
    chromium_markup = _page_html(fixture, fixture.pages[0])
    assert "running-header" in chromium_markup
    assert "running-footer" in chromium_markup
    assert "— ١ —" in chromium_markup


def test_heading_tag_matches_larger_heading_render(tmp_path: Path) -> None:
    fixture = _fixture("ar_single_column")
    target = tmp_path / "heading.pdf"
    _create_pdf(fixture, target)
    document = pymupdf.open(target)
    try:
        spans = [
            span
            for block in document[0].get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
            for span in line["spans"]
        ]
    finally:
        document.close()
    assert max(float(span["size"]) for span in spans) > min(
        float(span["size"]) for span in spans
    )
