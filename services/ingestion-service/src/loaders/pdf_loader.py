"""Load the file and return its content"""

import logging
from pathlib import Path
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


def load_pdf(file_path: str | Path) -> str:
    """Extract text from every page of a PDF."""
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            text = " ".join(text.split())
            pages.append(text)
    return "\n\n".join(pages)


if __name__ == "__main__":
    import sys
    text = load_pdf(sys.argv[1])
    print(f"Total characters: {len(text)}")
    print(f"Total words: {len(text.split())}")
    print(text[:20000]) 