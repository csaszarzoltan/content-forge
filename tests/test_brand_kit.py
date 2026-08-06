"""Interface and behavioral tests for brand_kit module.

Interface tests  — verify imports, class/function signatures (should PASS).
Behavioral tests — verify expected runtime behavior (should FAIL with
                    NotImplementedError until implementations are written).
"""
from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

# ── P0: Core ORM & Schemas ──────────────────────────────────────────────────

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.brand_kit.guidelines import BrandGuidelinesGenerator
from src.brand_kit.storage import BrandKitStorage
from src.models.brand_kit import BrandKit
from src.schemas.brand_kit import (
    BrandKitCreate,
    BrandKitListResponse,
    BrandKitResponse,
    BrandKitUpdate,
    ColorPalette,
    FontSet,
    LogoSet,
)

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestBrandKitORMInterface:
    """Verify the BrandKit ORM model interface."""

    def test_brand_kit_importable(self):
        assert BrandKit is not None

    def test_brand_kit_tablename(self):
        assert BrandKit.__tablename__ == "brand_kits"

    def test_brand_kit_expected_columns(self):
        """Expected columns declared as class annotations."""
        expected = {
            "id", "name", "description", "brand_type", "user_id",
            "brand_voice_id", "colors", "fonts", "logos", "version",
            "deleted_at", "created_at", "updated_at",
        }
        assert expected <= set(BrandKit.__annotations__)

    def test_brand_kit_has_soft_delete(self):
        assert hasattr(BrandKit, "soft_delete")
        assert callable(BrandKit.soft_delete)

    def test_brand_kit_has_increment_version(self):
        assert hasattr(BrandKit, "increment_version")
        assert callable(BrandKit.increment_version)


class TestColorPaletteInterface:
    """Verify the ColorPalette Pydantic model interface."""

    def test_color_palette_importable(self):
        assert ColorPalette is not None

    def test_color_palette_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ColorPalette, BaseModel)

    def test_color_palette_fields(self):
        sig = inspect.signature(ColorPalette)
        params = sig.parameters
        assert "primary" in params
        assert "secondary" in params
        assert "accent" in params
        assert "background" in params
        assert "text" in params

    def test_color_palette_has_primary_rgb(self):
        assert hasattr(ColorPalette, "primary_rgb")
        assert callable(ColorPalette.primary_rgb.fget)

    def test_color_palette_has_primary_hsl(self):
        assert hasattr(ColorPalette, "primary_hsl")
        assert callable(ColorPalette.primary_hsl.fget)


class TestFontSetInterface:
    """Verify the FontSet Pydantic model interface."""

    def test_font_set_importable(self):
        assert FontSet is not None

    def test_font_set_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(FontSet, BaseModel)

    def test_font_set_fields(self):
        sig = inspect.signature(FontSet)
        params = sig.parameters
        assert "heading" in params
        assert "body" in params
        assert "accent" in params
        assert "heading_file" in params
        assert "body_file" in params
        assert "accent_file" in params


class TestLogoSetInterface:
    """Verify the LogoSet Pydantic model interface."""

    def test_logo_set_importable(self):
        assert LogoSet is not None

    def test_logo_set_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(LogoSet, BaseModel)

    def test_logo_set_fields(self):
        sig = inspect.signature(LogoSet)
        params = sig.parameters
        assert "primary" in params
        assert "secondary" in params
        assert "icon" in params
        assert "watermark" in params
        assert "primary_format" in params
        assert "primary_size" in params


class TestBrandKitSchemasInterface:
    """Verify the brand kit schema interfaces."""

    def test_brand_kit_create_importable(self):
        assert BrandKitCreate is not None

    def test_brand_kit_create_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(BrandKitCreate, BaseModel)

    def test_brand_kit_create_fields(self):
        sig = inspect.signature(BrandKitCreate)
        params = sig.parameters
        assert "name" in params
        assert "description" in params
        assert "brand_type" in params
        assert "user_id" in params
        assert "brand_voice_id" in params
        assert "colors" in params
        assert "fonts" in params
        assert "logos" in params

    def test_brand_kit_update_importable(self):
        assert BrandKitUpdate is not None

    def test_brand_kit_update_all_fields_optional(self):
        sig = inspect.signature(BrandKitUpdate)
        for name, param in sig.parameters.items():
            assert param.default is None or param.default is not inspect.Parameter.empty, (
                f"Field '{name}' should be optional"
            )

    def test_brand_kit_response_importable(self):
        assert BrandKitResponse is not None

    def test_brand_kit_response_fields(self):
        sig = inspect.signature(BrandKitResponse)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "description" in sig.parameters
        assert "brand_type" in sig.parameters
        assert "colors" in sig.parameters
        assert "fonts" in sig.parameters
        assert "logos" in sig.parameters
        assert "version" in sig.parameters
        assert "created_at" in sig.parameters
        assert "updated_at" in sig.parameters

    def test_brand_kit_list_response_importable(self):
        assert BrandKitListResponse is not None

    def test_brand_kit_list_response_fields(self):
        sig = inspect.signature(BrandKitListResponse)
        assert "items" in sig.parameters
        assert "total" in sig.parameters
        assert "limit" in sig.parameters
        assert "offset" in sig.parameters


class TestBrandKitStorageInterface:
    """Verify the BrandKitStorage class interface."""

    def test_brand_kit_storage_importable(self):
        assert BrandKitStorage is not None

    def test_brand_kit_storage_is_class(self):
        assert inspect.isclass(BrandKitStorage)

    def test_brand_kit_storage_has_save_font(self):
        assert hasattr(BrandKitStorage, "save_font")
        assert callable(BrandKitStorage.save_font)

    def test_brand_kit_storage_has_save_logo(self):
        assert hasattr(BrandKitStorage, "save_logo")
        assert callable(BrandKitStorage.save_logo)

    def test_brand_kit_storage_has_delete_file(self):
        assert hasattr(BrandKitStorage, "delete_file")
        assert callable(BrandKitStorage.delete_file)

    def test_brand_kit_storage_has_validate_filename(self):
        assert hasattr(BrandKitStorage, "validate_filename")
        assert callable(BrandKitStorage.validate_filename)

    def test_brand_kit_storage_has_validate_file_type(self):
        assert hasattr(BrandKitStorage, "validate_file_type")
        assert callable(BrandKitStorage.validate_file_type)


class TestBrandGuidelinesGeneratorInterface:
    """Verify the BrandGuidelinesGenerator class interface."""

    def test_brand_guidelines_generator_importable(self):
        assert BrandGuidelinesGenerator is not None

    def test_brand_guidelines_generator_is_class(self):
        assert inspect.isclass(BrandGuidelinesGenerator)

    def test_brand_guidelines_generator_has_generate(self):
        assert hasattr(BrandGuidelinesGenerator, "generate")
        assert callable(BrandGuidelinesGenerator.generate)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (drive implementation)
# ============================================================================


class TestColorPaletteBehavioral:
    """Behavioral tests for ColorPalette — should fail on stubs."""

    def test_hex_validation_rejects_non_hex(self):
        """ColorPalette should reject non-hex color strings."""
        with pytest.raises(ValidationError):
            ColorPalette(primary="not-a-hex-color")

    def test_primary_rgb_returns_tuple_of_ints(self):
        """primary_rgb computed property should return (r, g, b) as ints."""
        palette = ColorPalette(primary="#ff8800")
        rgb = palette.primary_rgb
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3
        assert all(isinstance(v, int) for v in rgb)
        assert rgb == (255, 136, 0)

    def test_primary_hsl_returns_tuple(self):
        """primary_hsl computed property should return (h, s, l) tuple."""
        palette = ColorPalette(primary="#ff0000")
        hsl = palette.primary_hsl
        assert isinstance(hsl, tuple)
        assert len(hsl) == 3
        assert hsl[0] == 0  # pure red = hue 0
        assert hsl[1] == 100  # full saturation
        assert hsl[2] == 50  # 50% lightness


class TestBrandKitORMBehavioral:
    """Behavioral tests for BrandKit ORM — should fail on stubs."""

    async def test_brand_kit_create_and_read(self, db_session):
        """Create a BrandKit, commit, and read it back."""
        kit = BrandKit(
            name="Test Brand",
            description="A test brand kit",
            brand_type="personal",
        )
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)
        assert kit.id is not None
        assert kit.name == "Test Brand"
        assert kit.version == 1

    async def test_brand_kit_soft_delete_in_db(self, db_session):
        """soft_delete() should set deleted_at timestamp."""
        kit = BrandKit(name="To Delete")
        db_session.add(kit)
        await db_session.commit()
        kit.soft_delete()
        assert kit.deleted_at is not None

    async def test_brand_kit_increment_version_in_db(self, db_session):
        """increment_version() should bump version from 1 to 2."""
        kit = BrandKit(name="Versioned Kit")
        db_session.add(kit)
        await db_session.commit()
        assert kit.version == 1
        kit.increment_version()
        assert kit.version == 2


class TestBrandKitStorageBehavioral:
    """Behavioral tests for BrandKitStorage — should fail on stubs."""

    def test_save_font_creates_dir_and_file(self, tmp_path):
        """save_font should create the correct directory structure."""
        storage = BrandKitStorage(tmp_path)
        # When __init__ is implemented, save_font must create
        # {upload_root}/brand_kit/{kit_id}/fonts/{filename}
        async def _run():
            path = await storage.save_font("kit-1", "heading.ttf", b"fake font data")
            assert path.endswith("heading.ttf")
            full = tmp_path / "brand_kit" / "kit-1" / "fonts" / "heading.ttf"
            assert full.exists()

        import asyncio
        asyncio.run(_run())

    def test_save_logo_creates_dir_and_file(self, tmp_path):
        """save_logo should create the correct directory structure."""
        storage = BrandKitStorage(tmp_path)
        async def _run():
            path = await storage.save_logo("kit-1", "primary.png", b"fake image data")
            assert path.endswith("primary.png")
            full = tmp_path / "brand_kit" / "kit-1" / "logos" / "primary.png"
            assert full.exists()

        import asyncio
        asyncio.run(_run())

    def test_validate_filename_strips_path_components(self):
        """validate_filename should strip directory components."""
        result = BrandKitStorage.validate_filename("fonts/heading.ttf")
        assert result == "heading.ttf"

    def test_validate_filename_rejects_path_traversal(self):
        """validate_filename should reject path traversal attempts."""
        with pytest.raises(ValueError):
            BrandKitStorage.validate_filename("../../etc/passwd")

    def test_validate_file_type_accepts_font_extensions(self):
        """validate_file_type should accept .ttf, .otf, .woff2 for fonts."""
        allowed = {".ttf", ".otf", ".woff", ".woff2"}
        for ext in (".ttf", ".otf", ".woff2"):
            assert BrandKitStorage.validate_file_type(f"font{ext}", allowed)

    def test_validate_file_type_rejects_bad_font_extensions(self):
        """validate_file_type should reject .exe and .bat for fonts."""
        allowed = {".ttf", ".otf", ".woff", ".woff2"}
        for ext in (".exe", ".bat"):
            assert not BrandKitStorage.validate_file_type(f"file{ext}", allowed)

    def test_validate_file_type_accepts_logo_extensions(self):
        """validate_file_type should accept .png, .svg, .jpg, .webp for logos."""
        allowed = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
        for ext in (".png", ".svg", ".jpg", ".webp"):
            assert BrandKitStorage.validate_file_type(f"logo{ext}", allowed)

    def test_validate_file_type_rejects_exe_for_logos(self):
        """validate_file_type should reject .exe for logos."""
        allowed = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
        assert not BrandKitStorage.validate_file_type("malware.exe", allowed)


class TestBrandGuidelinesGeneratorBehavioral:
    """Behavioral tests for BrandGuidelinesGenerator — should fail on stubs."""

    def test_generate_returns_html_with_kit_name(self):
        """generate() should return HTML string containing the kit name."""
        gen = BrandGuidelinesGenerator()
        kit = BrandKitResponse(
            id="test", name="Acme Corp Brand", description="Main brand",
            brand_type="personal", colors=ColorPalette(),
            fonts=FontSet(), logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        result = gen.generate(kit)
        assert isinstance(result, str)
        assert "Acme Corp Brand" in result

    def test_generate_contains_color_hex_values(self):
        """generate() should contain color hex values from the palette."""
        gen = BrandGuidelinesGenerator()
        palette = ColorPalette(primary="#1a73e8", secondary="#ffffff", accent="#ea4335")
        kit = BrandKitResponse(
            id="test", name="Color Brand", description="",
            brand_type="personal", colors=palette,
            fonts=FontSet(), logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        result = gen.generate(kit)
        assert "#1a73e8" in result
        assert "#ffffff" in result
        assert "#ea4335" in result

    def test_generate_contains_font_names(self):
        """generate() should contain font names from the font set."""
        gen = BrandGuidelinesGenerator()
        fonts = FontSet(heading="Google Sans", body="Roboto", accent="Product Sans")
        kit = BrandKitResponse(
            id="test", name="Font Brand", description="",
            brand_type="personal", colors=ColorPalette(),
            fonts=fonts, logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        result = gen.generate(kit)
        assert "Google Sans" in result
        assert "Roboto" in result

    def test_generate_contains_voice_section_with_profile(self):
        """generate() should include voice section when voice_profile provided."""
        gen = BrandGuidelinesGenerator()
        kit = BrandKitResponse(
            id="test", name="Voice Brand", description="",
            brand_type="personal", colors=ColorPalette(),
            fonts=FontSet(), logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        voice = {"brand_identity": {"who": "Acme Corp", "audience": "Engineers"}}
        result = gen.generate(kit, voice_profile=voice)
        assert "voice" in result.lower()
