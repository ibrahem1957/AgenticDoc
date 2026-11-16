from __future__ import annotations

from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent


def main() -> None:
    text_pdf = pymupdf.open()
    page = text_pdf.new_page(width=300, height=200)
    page.insert_text((30, 60), "Synthetic PDF 2025", fontsize=14)
    text_pdf.set_metadata(
        {"producer": "AgenticDoc synthetic test", "creator": "generate_test_data.py"}
    )
    text_pdf.save(ROOT / "text.pdf", deflate=True)
    text_pdf.close()

    image = Image.new("RGB", (220, 80), "white")
    ImageDraw.Draw(image).text((10, 25), "Synthetic raster text", fill="black")
    image.save(ROOT / "image.png", optimize=True)

    image_pdf = pymupdf.open()
    page = image_pdf.new_page(width=300, height=200)
    page.insert_image(pymupdf.Rect(30, 50, 270, 140), filename=ROOT / "image.png")
    image_pdf.set_metadata(
        {"producer": "AgenticDoc synthetic test", "creator": "generate_test_data.py"}
    )
    image_pdf.save(ROOT / "image_only.pdf", deflate=True)
    image_pdf.close()


if __name__ == "__main__":
    main()
