"""Render and extract every PDF page for human review; never connect to MongoDB.

Run from the repo root: backend/.venv/Scripts/python backend/tools/review_brochure.py
Requires the optional backend/requirements-brochure.txt dependency.
"""
from pathlib import Path
import hashlib
import json
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'docs' / 'brochure'
PDF = FOLDER / 'Core Product A5 (2).pdf'


def main():
    output = FOLDER / 'review'
    output.mkdir(exist_ok=True)
    document = pdfium.PdfDocument(str(PDF))
    pages = []
    for index in range(len(document)):
        page = document[index]
        text_page = page.get_textpage()
        text = text_page.get_text_bounded()
        text_page.close()
        (output / f'page-{index+1:02}.txt').write_text(text, encoding='utf-8')
        bitmap = page.render(scale=1.6)
        bitmap.to_pil().save(output / f'page-{index+1:02}.png')
        bitmap.close()
        if index == 10:
            table_bitmap = page.render(scale=3)
            table_bitmap.to_pil().save(output / 'page-11-tables.png')
            table_bitmap.close()
        pages.append({'page': index+1, 'width': page.get_width(), 'height': page.get_height(), 'characters': len(text)})
        page.close()
    document.close()
    summary = {'filename': PDF.name, 'sha256': hashlib.sha256(PDF.read_bytes()).hexdigest(), 'pages': pages}
    (output / 'source.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
