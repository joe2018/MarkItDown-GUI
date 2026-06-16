"""Domain constants shared across modules.

Anything that is **not** UI text (use `i18n.py` for that) and **not**
configurable by the user (use `AppConfig` for that) lives here.
"""

from __future__ import annotations


# File extensions the GUI accepts. Image and audio are intentionally
# excluded: they require exiftool / ffmpeg / an LLM client to produce
# useful output, and silently returning empty markdown is a poor UX.
# Add extensions here when supporting a new text-type converter.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    # Office
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".pptx",
    ".msg",  # Outlook
    # Web / markup
    ".html",
    ".htm",
    ".xml",
    ".md",
    # Plain text formats
    ".txt",
    ".csv",
    ".json",
    ".rtf",
    # E-book
    ".epub",
    # Notebook
    ".ipynb",
    # Archives (the converter iterates the contents)
    ".zip",
    # Feeds
    ".rss",
)


def is_supported(path_like: str) -> bool:
    """Return True if the given file path's extension is in SUPPORTED_EXTENSIONS.

    Case-insensitive on the extension; leading dot optional in input.
    """
    if "." not in path_like:
        return False
    ext = "." + path_like.rsplit(".", 1)[-1].lower()
    return ext in SUPPORTED_EXTENSIONS
