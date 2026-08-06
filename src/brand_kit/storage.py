"""File storage utilities for brand kit assets (fonts, logos)."""
from __future__ import annotations

import re
from pathlib import Path

FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}

# Pattern for allowed characters in filenames
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-. ]*$")


class BrandKitStorage:
    """Handles font/logo file storage for brand kits."""

    def __init__(self, upload_root: str | Path) -> None:
        self.upload_root = Path(upload_root)

    async def save_font(self, brand_kit_id: str, filename: str, data: bytes) -> str:
        """Save a font file and return its relative path."""
        filename = self.validate_filename(filename)
        font_dir = self.upload_root / "brand_kit" / brand_kit_id / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        dest = font_dir / filename
        dest.write_bytes(data)
        return str(dest.relative_to(self.upload_root))

    async def save_logo(self, brand_kit_id: str, filename: str, data: bytes) -> str:
        """Save a logo file and return its relative path."""
        filename = self.validate_filename(filename)
        logo_dir = self.upload_root / "brand_kit" / brand_kit_id / "logos"
        logo_dir.mkdir(parents=True, exist_ok=True)
        dest = logo_dir / filename
        dest.write_bytes(data)
        return str(dest.relative_to(self.upload_root))

    async def delete_file(self, file_path: str) -> None:
        """Delete a file by its relative path."""
        full = self.upload_root / file_path
        if full.exists():
            full.unlink()

    def get_file_url(self, file_path: str) -> str:
        """Return the URL for a stored file."""
        return f"/static/brand_kit/{file_path}"

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Sanitize a filename: strip directory components, reject path traversal."""
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Path traversal not allowed: {filename}")
        name = Path(filename).name
        if not name:
            raise ValueError("Empty filename after sanitization")
        return name

    @staticmethod
    def validate_file_type(filename: str, allowed: set[str]) -> bool:
        """Validate that a filename has an allowed extension."""
        ext = Path(filename).suffix.lower()
        return ext in allowed
