"""Load a plain text (.txt / .md) file."""

from pathlib import Path


def load_txt(file_path: str | Path) -> str:
    """Read a text file with UTF-8 encoding (ignore bad bytes)."""
    return Path(file_path).read_text(encoding="utf-8", errors="ignore")
