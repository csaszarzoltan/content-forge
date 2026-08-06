"""Brand guidelines HTML generator."""
from __future__ import annotations

from src.brand_kit.storage import BrandKitStorage
from src.schemas.brand_kit import BrandKitResponse


class BrandGuidelinesGenerator:
    """Generate a self-contained HTML brand guidelines document."""

    def __init__(self, storage: BrandKitStorage | None = None) -> None:
        self.storage = storage

    def generate(self, kit: BrandKitResponse, voice_profile: dict | None = None) -> str:
        """Generate HTML brand guidelines."""
        colors = kit.colors
        fonts = kit.fonts
        logos = kit.logos

        color_swatches = f"""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin:16px 0">
          <div><div style="width:80px;height:80px;border-radius:8px;background:{colors.primary}"></div><small>Primary<br>{colors.primary}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{colors.secondary};border:1px solid #ccc"></div><small>Secondary<br>{colors.secondary}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{colors.accent}"></div><small>Accent<br>{colors.accent}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{colors.background};border:1px solid #ccc"></div><small>Background<br>{colors.background}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{colors.text}"></div><small>Text<br>{colors.text}</small></div>
        </div>"""

        font_section = f"""
        <h2>Typography</h2>
        <p><strong>Heading:</strong> {fonts.heading}</p>
        <p><strong>Body:</strong> {fonts.body}</p>
        <p><strong>Accent:</strong> {fonts.accent}</p>"""

        logo_section = ""
        if logos.primary or logos.secondary or logos.icon:
            logo_section = """
        <h2>Logos</h2>
        <ul>"""
            for label, path in [("Primary", logos.primary), ("Secondary", logos.secondary),
                                ("Icon", logos.icon), ("Watermark", logos.watermark)]:
                if path:
                    logo_section += f"<li><strong>{label}:</strong> {path}</li>"
            logo_section += "</ul>"

        voice_section = ""
        if voice_profile:
            identity = voice_profile.get("brand_identity", {})
            voice_section = f"""
        <h2>Brand Voice</h2>
        <p>{identity}</p>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{kit.name} — Brand Guidelines</title>
<style>
  body {{ font-family: {fonts.body}, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; color: {colors.text}; background: {colors.background}; }}
  h1 {{ color: {colors.primary}; font-family: {fonts.heading}, sans-serif; }}
  h2 {{ color: {colors.primary}; border-bottom: 2px solid {colors.accent}; padding-bottom: 4px; }}
</style>
</head>
<body>
<h1>{kit.name}</h1>
<p>{kit.description}</p>
<h2>Color Palette</h2>
{color_swatches}
{font_section}
{logo_section}
{voice_section}
</body>
</html>"""

    def generate_bytes(self, kit: BrandKitResponse, voice_profile: dict | None = None) -> bytes:
        """Generate HTML brand guidelines as bytes."""
        return self.generate(kit, voice_profile).encode("utf-8")
