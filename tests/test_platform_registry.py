"""Pre-development tests for platform constraint registry.

Interface tests: ConstraintRegistry class exists, methods exist, signatures.
Behavioral tests: Load, get, all_platforms, update, export — all raise NotImplementedError.
"""
from __future__ import annotations

import inspect

import pytest

from src.constraints.registry import ConstraintRegistry
from src.constraints.models import PlatformConstraints, TextConstraints

# ---------------------------------------------------------------------------
# Interface tests — must PASS immediately
# ---------------------------------------------------------------------------

class TestConstraintRegistryInterface:
    """Verify ConstraintRegistry class and method signatures."""

    def test_class_importable(self):
        assert ConstraintRegistry is not None

    def test_class_instantiable_with_no_args(self):
        reg = ConstraintRegistry()
        assert reg is not None

    def test_class_instantiable_with_path(self):
        reg = ConstraintRegistry(registry_path="/tmp/test.json")
        assert reg is not None

    def test_has_load_method(self):
        assert hasattr(ConstraintRegistry, "load")

    def test_has_get_method(self):
        assert hasattr(ConstraintRegistry, "get")

    def test_has_all_platforms_method(self):
        assert hasattr(ConstraintRegistry, "all_platforms")

    def test_has_platform_names_method(self):
        assert hasattr(ConstraintRegistry, "platform_names")

    def test_has_version_property(self):
        assert hasattr(ConstraintRegistry, "version")

    def test_has_update_method(self):
        assert hasattr(ConstraintRegistry, "update")

    def test_has_export_method(self):
        assert hasattr(ConstraintRegistry, "export")

    def test_load_signature(self):
        sig = inspect.signature(ConstraintRegistry.load)
        params = list(sig.parameters.keys())
        assert "self" in params

    def test_get_signature(self):
        sig = inspect.signature(ConstraintRegistry.get)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params

    def test_get_return_annotation(self):
        sig = inspect.signature(ConstraintRegistry.get)
        # with from __future__ import annotations, return annotation is a string
        ret = sig.return_annotation
        assert ret is not inspect.Parameter.empty

    def test_all_platforms_return_annotation(self):
        sig = inspect.signature(ConstraintRegistry.all_platforms)
        ret = sig.return_annotation
        # Should return dict[str, PlatformConstraints]
        assert ret is not inspect.Parameter.empty

    def test_update_signature(self):
        sig = inspect.signature(ConstraintRegistry.update)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params
        assert "constraints" in params

    def test_export_signature(self):
        sig = inspect.signature(ConstraintRegistry.export)
        params = list(sig.parameters.keys())
        assert "self" in params

    def test_version_is_property(self):
        # Verify it's defined on the class (property or method)
        assert "version" in dir(ConstraintRegistry)


# ---------------------------------------------------------------------------
# Behavioral tests — must FAIL (NotImplementedError)
# ---------------------------------------------------------------------------

class TestConstraintRegistryBehavior:
    """Behavioral: all methods raise NotImplementedError until implemented."""

    @pytest.mark.unit
    def test_load_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            reg.load()

    @pytest.mark.unit
    def test_get_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            reg.get("twitter")

    @pytest.mark.unit
    def test_all_platforms_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            reg.all_platforms()

    @pytest.mark.unit
    def test_platform_names_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            reg.platform_names()

    @pytest.mark.unit
    def test_version_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            _ = reg.version

    @pytest.mark.unit
    def test_update_raises_not_implemented(self):
        reg = ConstraintRegistry()
        constraints = PlatformConstraints(
            display_name="Test",
            text=TextConstraints(max_chars=100),
        )
        with pytest.raises(NotImplementedError):
            reg.update("twitter", constraints)

    @pytest.mark.unit
    def test_export_raises_not_implemented(self):
        reg = ConstraintRegistry()
        with pytest.raises(NotImplementedError):
            reg.export()

    # Future behavioral tests (skip during RED phase, active after implementation)

    @pytest.mark.unit
    def test_load_populates_platforms(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        platforms = reg.platform_names()
        assert "twitter" in platforms
        assert "linkedin" in platforms
        assert "instagram" in platforms
        assert "facebook" in platforms
        assert "tiktok" in platforms

    @pytest.mark.unit
    def test_get_twitter_returns_text_constraints(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        twitter = reg.get("twitter")
        assert twitter.text.max_chars == 280

    @pytest.mark.unit
    def test_get_linkedin_returns_text_constraints(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        linkedin = reg.get("linkedin")
        assert linkedin.text.max_chars == 3000

    @pytest.mark.unit
    def test_get_instagram_rejects_png(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        instagram = reg.get("instagram")
        assert "png" in instagram.image.rejected_formats

    @pytest.mark.unit
    def test_get_unknown_platform_raises(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        with pytest.raises(KeyError):
            reg.get("myspace")

    @pytest.mark.unit
    def test_all_platforms_returns_5(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        all_p = reg.all_platforms()
        assert len(all_p) == 5

    @pytest.mark.unit
    def test_version_returns_string(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(reg.version, str)
        assert reg.version.startswith("1.")

    @pytest.mark.unit
    def test_export_returns_dict(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        result = reg.export()
        assert isinstance(result, dict)
        assert "version" in result
        assert "platforms" in result

    @pytest.mark.unit
    def test_update_modifies_platform(self):
        try:
            reg = ConstraintRegistry()
            reg.load()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        new_constraints = PlatformConstraints(
            display_name="Twitter/X (Updated)",
            text=TextConstraints(max_chars=280),
        )
        reg.update("twitter", new_constraints)
        assert reg.get("twitter").display_name == "Twitter/X (Updated)"
