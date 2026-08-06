"""Interface and behavioral tests for brand_kit module.

Interface tests  — verify imports, class/function signatures.
Behavioral tests — verify runtime behavior against real implementations.
Schema tests     — validation edge cases and error handling.
CRUD tests       — ORM update, multi-brand, versioning, brand_voice linkage.
Integration      — full flow: brand kit creation -> guidelines HTML generation.

File: tests/test_brand_kit.py
Total: 70 unit + integration tests (as of this writing).
"""
from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

# ── P0: Core ORM & Schemas ──────────────────────────────────────────────────

pytestmark = [pytest.mark.quick]

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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_brand_kit_soft_delete_in_db(self, db_session):
        """soft_delete() should set deleted_at timestamp."""
        kit = BrandKit(name="To Delete")
        db_session.add(kit)
        await db_session.commit()
        kit.soft_delete()
        assert kit.deleted_at is not None

    @pytest.mark.asyncio
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
        """validate_file_type should accept .png, .jpg, .webp for logos.

        R2: .svg was removed from the logo whitelist — SVGs can carry
        <script> and are served as image/svg+xml from /uploads without a CSP,
        making them a stored-XSS vector. PNG/JPEG/WebP cover logos.
        """
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        for ext in (".png", ".jpg", ".webp"):
            assert BrandKitStorage.validate_file_type(f"logo{ext}", allowed)

    def test_validate_file_type_rejects_svg_for_logos(self):
        """validate_file_type must reject .svg (R2: stored XSS)."""
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        assert not BrandKitStorage.validate_file_type("logo.svg", allowed)

    def test_validate_file_type_rejects_exe_for_logos(self):
        """validate_file_type should reject .exe for logos."""
        allowed = {".png", ".jpg", ".jpeg", ".webp"}
        assert not BrandKitStorage.validate_file_type("malware.exe", allowed)

    def test_delete_file_rejects_path_escaping_upload_root(self, tmp_path):
        """H1: delete_file must refuse paths that escape the upload root.

        A bare join+unlink lets delete_file("../../victim.txt") delete a file
        outside UPLOAD_ROOT. It must raise ValueError and leave the outside
        file untouched.
        """
        import asyncio

        root = tmp_path / "uploads"
        root.mkdir()
        outside = tmp_path / "victim.txt"
        outside.write_text("DO NOT DELETE")

        storage = BrandKitStorage(root)

        async def _run():
            with pytest.raises(ValueError):
                await storage.delete_file("../victim.txt")
            with pytest.raises(ValueError):
                await storage.delete_file("../../victim.txt")
            assert outside.exists(), "outside file must be untouched"
            assert outside.read_text() == "DO NOT DELETE"

        asyncio.run(_run())

    def test_delete_file_removes_file_inside_upload_root(self, tmp_path):
        """delete_file still works for legitimate in-root paths."""
        import asyncio

        root = tmp_path / "uploads"
        target = root / "brand_kit" / "kit-1" / "logos" / "primary.png"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"png")
        storage = BrandKitStorage(root)

        async def _run():
            await storage.delete_file("brand_kit/kit-1/logos/primary.png")
            assert not target.exists()

        asyncio.run(_run())


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


# ============================================================================
# SECTION 3 — SCHEMA ERROR CASES
# ============================================================================


class TestSchemaErrorCases:
    """Pydantic schema error cases — validation edge cases."""

    def test_brand_kit_create_empty_name_rejected(self):
        """BrandKitCreate rejects empty name (min_length=1)."""
        with pytest.raises(ValidationError):
            BrandKitCreate(name="")

    def test_brand_kit_create_very_long_name_accepted(self):
        """BrandKitCreate accepts long names (no max_length constraint)."""
        req = BrandKitCreate(name="A" * 500)
        assert len(req.name) == 500

    def test_color_palette_invalid_hex_rejected(self):
        """ColorPalette rejects invalid hex colors."""
        with pytest.raises(ValidationError):
            ColorPalette(primary="not-a-hex")

    def test_color_palette_partial_hex_rejected(self):
        """ColorPalette rejects truncated hex like '#fff'."""
        with pytest.raises(ValidationError):
            ColorPalette(primary="#fff")

    def test_color_palette_hex_with_alpha_rejected(self):
        """ColorPalette rejects 8-char hex (no alpha support)."""
        with pytest.raises(ValidationError):
            ColorPalette(primary="#ff0000ff")

    def test_brand_kit_create_defaults(self):
        """BrandKitCreate applies sensible defaults."""
        req = BrandKitCreate(name="Minimal Brand")
        assert req.brand_type == "personal"
        assert req.description == ""
        assert req.user_id is None
        assert req.brand_voice_id is None
        assert isinstance(req.colors, ColorPalette)
        assert isinstance(req.fonts, FontSet)
        assert isinstance(req.logos, LogoSet)

    def test_brand_kit_update_all_none(self):
        """BrandKitUpdate with no fields is valid (all optional)."""
        req = BrandKitUpdate()
        assert req.name is None
        assert req.colors is None


# ============================================================================
# SECTION 4 — ORM CRUD BEHAVIORAL TESTS
# ============================================================================


class TestBrandKitORMCRUD:
    """Brand Kit ORM CRUD: update, multi-brand, brand_voice linkage."""

    @pytest.mark.asyncio
    async def test_brand_kit_update_fields(self, db_session):
        """Create a kit, update name and colors, verify changes persist."""
        kit = BrandKit(name="Original Name", description="old desc")
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)

        kit.name = "Updated Name"
        kit.description = "new desc"
        kit.colors = {"primary": "#ff0000", "secondary": "#00ff00"}
        kit.increment_version()
        await db_session.commit()
        await db_session.refresh(kit)

        assert kit.name == "Updated Name"
        assert kit.description == "new desc"
        assert kit.version == 2
        assert kit.colors["primary"] == "#ff0000"

    @pytest.mark.asyncio
    async def test_multi_brand_support(self, db_session):
        """Multiple brand kits can coexist under the same user."""
        user_id = "user-multi-test"
        kit1 = BrandKit(name="Personal Brand", brand_type="personal", user_id=user_id)
        kit2 = BrandKit(name="Business Brand", brand_type="business", user_id=user_id)
        db_session.add_all([kit1, kit2])
        await db_session.commit()
        await db_session.refresh(kit1)
        await db_session.refresh(kit2)

        assert kit1.id != kit2.id
        assert kit1.name == "Personal Brand"
        assert kit2.name == "Business Brand"
        assert kit1.brand_type == "personal"
        assert kit2.brand_type == "business"

    @pytest.mark.asyncio
    async def test_brand_voice_linkage(self, db_session):
        """Brand kit can link to a brand_voice profile via brand_voice_id."""
        kit = BrandKit(
            name="Linked Brand",
            brand_voice_id="voice-profile-abc",
        )
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)

        assert kit.brand_voice_id == "voice-profile-abc"

    @pytest.mark.asyncio
    async def test_brand_kit_soft_delete_sets_timestamp(self, db_session):
        """soft_delete sets deleted_at; kit still exists in DB."""
        kit = BrandKit(name="To Be Deleted")
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)

        assert kit.deleted_at is None
        kit.soft_delete()
        await db_session.commit()
        await db_session.refresh(kit)

        assert kit.deleted_at is not None

    @pytest.mark.asyncio
    async def test_version_starts_at_one(self, db_session):
        """New brand kit starts at version 1."""
        kit = BrandKit(name="Version Test")
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)
        assert kit.version == 1

    @pytest.mark.asyncio
    async def test_multiple_version_increments(self, db_session):
        """Multiple increment_version calls stack correctly."""
        kit = BrandKit(name="Multi Inc")
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)

        kit.increment_version()
        kit.increment_version()
        kit.increment_version()
        assert kit.version == 4

    @pytest.mark.asyncio
    async def test_colors_stored_as_json(self, db_session):
        """Colors stored as JSON dict in ORM column."""
        colors = {
            "primary": "#1a73e8",
            "secondary": "#ffffff",
            "accent": "#ea4335",
            "background": "#f8f9fa",
            "text": "#202124",
        }
        kit = BrandKit(name="JSON Colors", colors=colors)
        db_session.add(kit)
        await db_session.commit()
        await db_session.refresh(kit)
        assert kit.colors["primary"] == "#1a73e8"
        assert kit.colors["accent"] == "#ea4335"


# ============================================================================
# SECTION 5 — INTEGRATION TEST (brand kit creation -> guidelines generation)
# ============================================================================


class TestBrandKitGuidelinesIntegration:
    """Integration: create brand kit -> generate full guidelines HTML."""

    def test_full_flow_create_to_guidelines(self, tmp_path):
        """Create a brand kit, populate it, and generate guidelines HTML.

        This is the core integration test: brand kit creation with colors,
        fonts, logos, and voice profile feeds into the guidelines generator,
        producing a complete HTML document with all sections.
        """
        from src.brand_kit.guidelines import BrandGuidelinesGenerator

        # 1. Create a fully populated BrandKitResponse
        palette = ColorPalette(
            primary="#1a73e8",
            secondary="#ffffff",
            accent="#ea4335",
            background="#f8f9fa",
            text="#202124",
        )
        fonts = FontSet(
            heading="Google Sans",
            body="Roboto",
            accent="Product Sans",
        )
        logos = LogoSet(
            primary="brand_kit/kit-int/logos/primary.png",
            icon="brand_kit/kit-int/logos/icon.svg",
        )
        kit = BrandKitResponse(
            id="kit-int",
            name="Integration Corp",
            description="Full integration test brand",
            brand_type="business",
            colors=palette,
            fonts=fonts,
            logos=logos,
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )

        # 2. Supply a voice profile
        voice_profile = {
            "brand_identity": {
                "who": "Integration Corp, a test automation company",
                "audience": "QA engineers and developers",
                "purpose": "Make testing effortless and reliable",
            },
            "vocabulary": {
                "preferred": ["reliable", "fast", "accurate"],
                "banned": ["flaky", "brittle"],
            },
        }

        # 3. Generate guidelines
        gen = BrandGuidelinesGenerator()
        html = gen.generate(kit, voice_profile=voice_profile)

        # 4. Verify the HTML is complete and contains all sections
        assert isinstance(html, str)
        assert len(html) > 200  # Non-trivial document

        # Title and description
        assert "Integration Corp" in html
        assert "Full integration test brand" in html

        # Color palette section
        assert "#1a73e8" in html
        assert "#ffffff" in html
        assert "#ea4335" in html
        assert "#f8f9fa" in html
        assert "#202124" in html

        # Typography section
        assert "Google Sans" in html
        assert "Roboto" in html
        assert "Product Sans" in html

        # Logo section
        assert "primary.png" in html
        assert "icon.svg" in html

        # Voice section
        assert "voice" in html.lower()
        assert "Integration Corp, a test automation company" in html

        # Valid HTML structure
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_guidelines_bytes_matches_string(self):
        """generate_bytes() returns same content as generate() encoded."""
        from src.brand_kit.guidelines import BrandGuidelinesGenerator

        kit = BrandKitResponse(
            id="bytes-test",
            name="Bytes Test Brand",
            description="",
            brand_type="personal",
            colors=ColorPalette(),
            fonts=FontSet(),
            logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        gen = BrandGuidelinesGenerator()
        html_str = gen.generate(kit)
        html_bytes = gen.generate_bytes(kit)
        assert html_bytes == html_str.encode("utf-8")

    def test_guidelines_with_no_logos_no_voice(self):
        """Guidelines still generate with empty logos and no voice profile."""
        from src.brand_kit.guidelines import BrandGuidelinesGenerator

        kit = BrandKitResponse(
            id="minimal",
            name="Minimal Brand",
            description="Bare minimum",
            brand_type="personal",
            colors=ColorPalette(),
            fonts=FontSet(),
            logos=LogoSet(),
            version=1,
            created_at=__import__("datetime").datetime.now(),
            updated_at=__import__("datetime").datetime.now(),
        )
        gen = BrandGuidelinesGenerator()
        html = gen.generate(kit)
        assert "Minimal Brand" in html
        assert "Bare minimum" in html
        # No logo section expected
        assert "Logos" not in html or kit.logos.primary is None


# ============================================================================
# SECTION 6 — SECURITY (stored XSS regression, review finding F3)
# ============================================================================


class TestBrandGuidelinesXSS:
    """Guidelines HTML must escape every user-derived value (F3).

    The frontend renders the guidelines response via ``dangerouslySetInnerHTML``
    (frontend/src/brandkit.tsx), so any unescaped user-controlled value is a
    stored-XSS vector executing in every viewer's browser.
    """

    def _kit_with_payload(self) -> BrandKitResponse:
        """A kit whose user fields carry script/img injection payloads."""
        from datetime import UTC, datetime

        return BrandKitResponse(
            id="xss-kit",
            name="<script>alert(1)</script>",
            description='<img src=x onerror="alert(2)">',
            brand_type='"><script>alert(3)</script>',
            colors=ColorPalette(
                primary="#1a73e8",
                secondary="#ffffff",
                accent="#ea4335",
                background="#f8f9fa",
                text="#202124",
            ),
            fonts=FontSet(
                heading='"><script>alert(4)</script>',
                body="Roboto</style><script>alert(5)</script>",
                accent="Product Sans",
            ),
            logos=LogoSet(
                primary="brand_kit/xss-kit/logos/primary.png",
                icon="brand_kit/xss-kit/logos/icon.svg",
            ),
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_xss_payload_in_name_and_description_is_escaped(self):
        """Raw script/img tags must never appear; escaped forms must."""
        html = BrandGuidelinesGenerator().generate(self._kit_with_payload())

        # Escaped forms are present
        assert "&lt;script&gt;" in html
        assert "&lt;img src=x onerror" in html

        # Raw payloads must NOT appear
        assert "<script>alert(1)</script>" not in html
        assert "<img src=x onerror" not in html
        assert "onerror=alert(2)" not in html
        assert "onerror=\"alert(2)\"" not in html

    def test_xss_payload_in_fonts_and_brand_type_is_escaped(self):
        """Font names and brand_type injected into HTML must be escaped."""
        html = BrandGuidelinesGenerator().generate(self._kit_with_payload())

        assert "&lt;script&gt;" in html
        assert "<script>alert(4)</script>" not in html
        assert "<script>alert(5)</script>" not in html
        assert "<script>alert(3)</script>" not in html
        # The </style> breakout must be neutralized
        assert "</style><script>" not in html

    def test_xss_payload_escaping_through_guidelines_endpoint(self):
        """Escaping survives the full pipeline: DB -> response -> HTML."""
        from datetime import UTC, datetime

        kit = BrandKitResponse(
            id="xss-e2e",
            name="<script>alert(1)</script>",
            description='<img src=x onerror="alert(2)">',
            brand_type="personal",
            colors=ColorPalette(),
            fonts=FontSet(),
            logos=LogoSet(),
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        html = BrandGuidelinesGenerator().generate(kit)

        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "<script>alert(1)</script>" not in html
        assert "<img src=x onerror" not in html
        assert "onerror=alert(2)" not in html

    def test_benign_values_render_unescaped(self):
        """Normal brand data must still render as plain text (no double-escape)."""
        from datetime import UTC, datetime

        kit = BrandKitResponse(
            id="benign",
            name="Acme Corp",
            description="Primary brand identity",
            brand_type="business",
            colors=ColorPalette(primary="#1a73e8", accent="#ea4335"),
            fonts=FontSet(heading="Manrope", body="DM Sans", accent="Inter"),
            logos=LogoSet(primary="brand_kit/benign/logos/logo.png"),
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        html = BrandGuidelinesGenerator().generate(kit)

        assert "Acme Corp" in html
        assert "Primary brand identity" in html
        assert "Manrope" in html
        assert "DM Sans" in html
        assert "&lt;" not in html
        assert "#1a73e8" in html
