"""Pydantic schemas for brand kit CRUD operations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ColorPalette(BaseModel):
    """Color palette with hex values and computed format conversions."""

    primary: str = Field("#000000", pattern=r"^#?[0-9A-Fa-f]{6}$")
    secondary: str = Field("#ffffff", pattern=r"^#?[0-9A-Fa-f]{6}$")
    accent: str = Field("#0066cc", pattern=r"^#?[0-9A-Fa-f]{6}$")
    background: str = Field("#ffffff", pattern=r"^#?[0-9A-Fa-f]{6}$")
    text: str = Field("#333333", pattern=r"^#?[0-9A-Fa-f]{6}$")

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    def _rgb_to_hsl(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """Convert RGB to HSL tuple."""
        r_norm, g_norm, b_norm = r / 255, g / 255, b / 255
        max_val = max(r_norm, g_norm, b_norm)
        min_val = min(r_norm, g_norm, b_norm)
        l = (max_val + min_val) / 2
        if max_val == min_val:
            h = s = 0.0
        else:
            d = max_val - min_val
            s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
            if max_val == r_norm:
                h = (g_norm - b_norm) / d + (6 if g_norm < b_norm else 0)
            elif max_val == g_norm:
                h = (b_norm - r_norm) / d + 2
            else:
                h = (r_norm - g_norm) / d + 4
            h /= 6
        return (round(h * 360), round(s * 100), round(l * 100))

    @property
    def primary_rgb(self) -> tuple[int, int, int]:
        return self._hex_to_rgb(self.primary)

    @property
    def primary_hsl(self) -> tuple[int, int, int]:
        r, g, b = self.primary_rgb
        return self._rgb_to_hsl(r, g, b)


class FontSet(BaseModel):
    """Font configuration for a brand kit."""

    heading: str = "Arial"
    body: str = "Arial"
    accent: str = "Arial"
    heading_file: str | None = None
    body_file: str | None = None
    accent_file: str | None = None


class LogoSet(BaseModel):
    """Logo file paths and metadata for a brand kit."""

    primary: str | None = None
    secondary: str | None = None
    icon: str | None = None
    watermark: str | None = None
    primary_format: str | None = None
    primary_size: int | None = None


class BrandKitCreate(BaseModel):
    """Request body for creating a new brand kit."""

    name: str = Field(..., min_length=1, description="Brand kit name")
    description: str = Field("", description="Brief description")
    brand_type: str = Field("personal", description="personal or business")
    user_id: str | None = None
    brand_voice_id: str | None = None
    colors: ColorPalette = Field(default_factory=ColorPalette)
    fonts: FontSet = Field(default_factory=FontSet)
    logos: LogoSet = Field(default_factory=LogoSet)


class BrandKitUpdate(BaseModel):
    """Request body for updating an existing brand kit (partial / PATCH)."""

    name: str | None = None
    description: str | None = None
    brand_type: str | None = None
    brand_voice_id: str | None = None
    colors: ColorPalette | None = None
    fonts: FontSet | None = None
    logos: LogoSet | None = None


class BrandKitResponse(BaseModel):
    """Response body representing a single brand kit."""

    id: str
    name: str
    description: str
    brand_type: str
    user_id: str | None = None
    brand_voice_id: str | None = None
    colors: ColorPalette = Field(default_factory=ColorPalette)
    fonts: FontSet = Field(default_factory=FontSet)
    logos: LogoSet = Field(default_factory=LogoSet)
    version: int
    created_at: datetime
    updated_at: datetime


class BrandKitListResponse(BaseModel):
    """Response body for listing brand kits (paginated)."""

    items: list[BrandKitResponse]
    total: int
    limit: int = 20
    offset: int = 0
