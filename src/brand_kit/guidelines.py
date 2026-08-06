"""Brand guidelines HTML generator."""
from __future__ import annotations

from html import escape

from src.brand_kit.storage import BrandKitStorage
from src.schemas.brand_kit import BrandKitResponse


class BrandGuidelinesGenerator:
    """Generate a self-contained HTML brand guidelines document."""

    def __init__(self, storage: BrandKitStorage | None = None) -> None:
        self.storage = storage

    def generate(self, kit: BrandKitResponse, voice_profile: dict | None = None) -> str:
        """Generate HTML brand guidelines.

        Every user-derived value (name, description, brand_type, fonts, and —
        defense-in-depth — colors, which are pattern-constrained) is HTML-
        escaped before interpolation. The generated document is rendered by
        the frontend via ``dangerouslySetInnerHTML``, so raw interpolation
        would be a stored-XSS vector (see F3 review finding).
        """
        colors = kit.colors
        fonts = kit.fonts
        logos = kit.logos

        # Escape user-derived values before any interpolation.
        name = escape(kit.name)
        description = escape(kit.description)
        brand_type = escape(kit.brand_type)
        heading_font = escape(fonts.heading)
        body_font = escape(fonts.body)
        accent_font = escape(fonts.accent)
        primary_color = escape(colors.primary)
        secondary_color = escape(colors.secondary)
        accent_color = escape(colors.accent)
        background_color = escape(colors.background)
        text_color = escape(colors.text)

        color_swatches = f"""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin:16px 0">
          <div><div style="width:80px;height:80px;border-radius:8px;background:{primary_color}"></div><small>Primary<br>{primary_color}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{secondary_color};border:1px solid #ccc"></div><small>Secondary<br>{secondary_color}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{accent_color}"></div><small>Accent<br>{accent_color}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{background_color};border:1px solid #ccc"></div><small>Background<br>{background_color}</small></div>
          <div><div style="width:80px;height:80px;border-radius:8px;background:{text_color}"></div><small>Text<br>{text_color}</small></div>
        </div>"""

        font_section = f"""
        <h2>Typography</h2>
        <p><strong>Heading:</strong> {heading_font}</p>
        <p><strong>Body:</strong> {body_font}</p>
        <p><strong>Accent:</strong> {accent_font}</p>"""

        logo_section = ""
        if logos.primary or logos.secondary or logos.icon:
            logo_section = """
        <h2>Logos</h2>
        <ul>"""
            for label, path in [("Primary", logos.primary), ("Secondary", logos.secondary),
                                ("Icon", logos.icon), ("Watermark", logos.watermark)]:
                if path:
                    logo_section += f"<li><strong>{escape(label)}:</strong> {escape(path)}</li>"
            logo_section += "</ul>"

        voice_section = ""
        if voice_profile:
            identity = voice_profile.get("brand_identity", {})
            # identity may be a dict from the voice profile; render its string
            # form and escape it so embedded HTML in voice data can't execute.
            voice_section = f"""
        <h2>Brand Voice</h2>
        <p>{escape(str(identity))}</p>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Brand Guidelines</title>
<style>
  body {{ font-family: {body_font}, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; color: {text_color}; background: {background_color}; }}
  h1 {{ color: {primary_color}; font-family: {heading_font}, sans-serif; }}
  h2 {{ color: {primary_color}; border-bottom: 2px solid {accent_color}; padding-bottom: 4px; }}
</style>
</head>
<body>
<h1>{name}</h1>
<p>{description}</p>
<p><small>{brand_type}</small></p>
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
