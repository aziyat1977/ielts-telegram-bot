"""
Usage (local):
  .venv/Scripts/python.exe tools/regen_passages.py "C:/Users/You/Downloads/Cambridge-IELTS-12-PDF.pdf"

Parses text with PyMuPDF. If Tesseract is installed, you can extend to image-OCR per page.
Writes app/data/reading_texts.py with EN/RU/UZ placeholders (keep RU/UZ empty to fill later).
"""
import sys, re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "reading_texts.py"

def clean(txt: str) -> list[str]:
    txt = re.sub(r"\r\n?", "\n", txt)
    blocks = [p.strip() for p in txt.split("\n\n") if p.strip()]
    return blocks[:10]  # keep small for Telegram

def main(pdf_path: str):
    doc = fitz.open(pdf_path)
    text = []
    for page in doc:
        text.append(page.get_text("text", sort=True))
    en_blocks = clean("\n\n".join(text))
    content = f'''BOOKS = ["Cambridge 12"]
TESTS = ["Test 5"]
PASSAGES = {{
    ("Cambridge 12","Test 5","Passage 1"): {{
        "title": "Generated from PDF",
        "english": {en_blocks!r},
        "ru": [],
        "uz": []
    }}
}}
'''
    OUT.write_text(content, encoding="utf-8")
    print(f"Written {OUT}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Provide path to Cambridge 12 PDF")
        sys.exit(1)
    main(sys.argv[1])
