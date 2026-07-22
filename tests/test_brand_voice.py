"""Interface and behavioral tests for brand_voice module.

Interface tests  — verify imports, class/function signatures (should PASS).
Behavioral tests — verify expected runtime behavior (should FAIL with NotImplementedError
                    until implementations are written).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

# ── P0: Core Models ─────────────────────────────────────────────────────────
from brand_voice.models import (
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)

# ── P0: Parser ──────────────────────────────────────────────────────────────
from brand_voice.parser import ParseError, parse_brand_voice, parse_brand_voice_string, validate_brand_voice

# ── P0: Presets ─────────────────────────────────────────────────────────────
from brand_voice.presets import PresetManager

# ── P0: Templates ───────────────────────────────────────────────────────────
from brand_voice.templates import TemplateEngine

# ── P1: Multi-Brand ─────────────────────────────────────────────────────────
from brand_voice.multi_brand import VoiceManager

# ── P1: Prompt Binding ──────────────────────────────────────────────────────
from brand_voice.prompt_binding import PromptBinder

# ── P1: Scoping ─────────────────────────────────────────────────────────────
from brand_voice.scoping import VoiceScope

# ── P2: Compliance ──────────────────────────────────────────────────────────
from brand_voice.compliance import ComplianceResult, ComplianceScorer

# ── P2: Extraction ──────────────────────────────────────────────────────────
from brand_voice.extraction import VoiceExtractor


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestModelsInterface:
    """Verify the models module interface."""

    def test_voice_attribute_importable(self):
        assert VoiceAttribute is not None

    def test_voice_attribute_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(VoiceAttribute, BaseModel)

    def test_voice_attribute_fields(self):
        sig = inspect.signature(VoiceAttribute)
        params = sig.parameters
        assert "name" in params
        assert "min_label" in params
        assert "max_label" in params
        assert "value" in params

    def test_vocabulary_rules_importable(self):
        assert VocabularyRules is not None

    def test_vocabulary_rules_fields(self):
        sig = inspect.signature(VocabularyRules)
        params = sig.parameters
        assert "preferred" in params
        assert "banned" in params
        assert "jargon_level" in params

    def test_scenario_tone_importable(self):
        assert ScenarioTone is not None

    def test_scenario_tone_fields(self):
        sig = inspect.signature(ScenarioTone)
        params = sig.parameters
        assert "scenario" in params
        assert "tone" in params
        assert "instructions" in params

    def test_formatting_prefs_importable(self):
        assert FormattingPrefs is not None

    def test_formatting_prefs_fields(self):
        sig = inspect.signature(FormattingPrefs)
        params = sig.parameters
        assert "heading_style" in params
        assert "bullet_style" in params
        assert "citation_format" in params

    def test_voice_profile_importable(self):
        assert VoiceProfile is not None

    def test_voice_profile_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(VoiceProfile, BaseModel)

    def test_voice_profile_fields(self):
        sig = inspect.signature(VoiceProfile)
        params = sig.parameters
        assert "id" in params
        assert "name" in params
        assert "description" in params
        assert "brand_identity" in params
        assert "attributes" in params
        assert "vocabulary" in params
        assert "scenarios" in params
        assert "formatting" in params
        assert "metadata" in params

    def test_voice_profile_has_to_system_prompt(self):
        assert hasattr(VoiceProfile, "to_system_prompt")
        assert callable(VoiceProfile.to_system_prompt)

    def test_voice_profile_to_system_prompt_return_annotation(self):
        sig = inspect.signature(VoiceProfile.to_system_prompt)
        # Annotation may be str type or string literal due to PEP 563
        ann = sig.return_annotation
        assert ann is not inspect.Parameter.empty

    def test_voice_profile_has_to_dict(self):
        assert hasattr(VoiceProfile, "to_dict")
        assert callable(VoiceProfile.to_dict)

    def test_voice_profile_to_dict_return_annotation(self):
        sig = inspect.signature(VoiceProfile.to_dict)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_voice_profile_has_from_dict(self):
        assert hasattr(VoiceProfile, "from_dict")
        assert callable(VoiceProfile.from_dict)

    def test_voice_profile_from_dict_is_classmethod(self):
        # Verify from_dict is a classmethod — callable without an instance
        assert hasattr(VoiceProfile, "from_dict")
        assert callable(VoiceProfile.from_dict)
        result = VoiceProfile.from_dict({
            "id": "test", "name": "T", "description": "D",
            "attributes": [],
            "vocabulary": {"preferred": [], "banned": [], "jargon_level": "none"},
            "scenarios": [],
            "formatting": {"heading_style": "s", "bullet_style": "d", "citation_format": "i"},
            "metadata": {},
        })
        assert result.id == "test"

    def test_voice_profile_has_docstring(self):
        doc = VoiceProfile.__doc__
        assert doc is not None and len(doc) > 10

    def test_models_module_has_all(self):
        from brand_voice import models
        assert hasattr(models, "__all__")
        assert len(models.__all__) >= 4


class TestParserInterface:
    """Verify the parser module interface."""

    def test_parse_error_importable(self):
        assert ParseError is not None

    def test_parse_error_is_exception(self):
        assert issubclass(ParseError, Exception)

    def test_parse_brand_voice_is_callable(self):
        assert callable(parse_brand_voice)

    def test_parse_brand_voice_signature(self):
        sig = inspect.signature(parse_brand_voice)
        assert "file_path" in sig.parameters

    def test_parse_brand_voice_return_annotation(self):
        sig = inspect.signature(parse_brand_voice)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_parse_brand_voice_has_docstring(self):
        doc = parse_brand_voice.__doc__
        assert doc is not None and len(doc) > 10

    def test_parse_brand_voice_is_function(self):
        assert inspect.isfunction(parse_brand_voice)

    def test_parse_brand_voice_string_is_callable(self):
        assert callable(parse_brand_voice_string)

    def test_parse_brand_voice_string_signature(self):
        sig = inspect.signature(parse_brand_voice_string)
        assert "content" in sig.parameters
        assert "source" in sig.parameters

    def test_parse_brand_voice_string_return_annotation(self):
        sig = inspect.signature(parse_brand_voice_string)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_parse_brand_voice_string_is_function(self):
        assert inspect.isfunction(parse_brand_voice_string)

    def test_validate_brand_voice_is_callable(self):
        assert callable(validate_brand_voice)

    def test_validate_brand_voice_signature(self):
        sig = inspect.signature(validate_brand_voice)
        assert "data" in sig.parameters

    def test_validate_brand_voice_return_annotation(self):
        sig = inspect.signature(validate_brand_voice)
        # Should return list[str]
        ann = sig.return_annotation
        assert ann is not inspect.Parameter.empty

    def test_validate_brand_voice_is_function(self):
        assert inspect.isfunction(validate_brand_voice)

    def test_parser_module_has_all(self):
        from brand_voice import parser
        assert hasattr(parser, "__all__")


class TestPresetsInterface:
    """Verify the presets module interface."""

    def test_preset_manager_importable(self):
        assert PresetManager is not None

    def test_preset_manager_is_class(self):
        assert inspect.isclass(PresetManager)

    def test_preset_manager_init_signature(self):
        sig = inspect.signature(PresetManager.__init__)
        assert "custom_dir" in sig.parameters

    def test_preset_manager_init_custom_dir_optional(self):
        sig = inspect.signature(PresetManager.__init__)
        param = sig.parameters["custom_dir"]
        assert param.default is None

    def test_preset_manager_has_list_builtins(self):
        assert hasattr(PresetManager, "list_builtins")
        assert callable(PresetManager.list_builtins)

    def test_preset_manager_list_builtins_return_annotation(self):
        sig = inspect.signature(PresetManager.list_builtins)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_preset_manager_has_list_custom(self):
        assert hasattr(PresetManager, "list_custom")

    def test_preset_manager_has_get_preset(self):
        assert hasattr(PresetManager, "get_preset")

    def test_preset_manager_get_preset_signature(self):
        sig = inspect.signature(PresetManager.get_preset)
        assert "name" in sig.parameters

    def test_preset_manager_has_save_custom(self):
        assert hasattr(PresetManager, "save_custom")

    def test_preset_manager_save_custom_signature(self):
        sig = inspect.signature(PresetManager.save_custom)
        assert "profile" in sig.parameters
        assert "name" in sig.parameters

    def test_preset_manager_has_delete_custom(self):
        assert hasattr(PresetManager, "delete_custom")

    def test_preset_manager_delete_custom_signature(self):
        sig = inspect.signature(PresetManager.delete_custom)
        assert "name" in sig.parameters

    def test_preset_manager_has_remix(self):
        assert hasattr(PresetManager, "remix")

    def test_preset_manager_remix_signature(self):
        sig = inspect.signature(PresetManager.remix)
        assert "base_name" in sig.parameters
        assert "overrides" in sig.parameters


class TestTemplatesInterface:
    """Verify the templates module interface."""

    def test_template_engine_importable(self):
        assert TemplateEngine is not None

    def test_template_engine_is_class(self):
        assert inspect.isclass(TemplateEngine)

    def test_template_engine_init_signature(self):
        sig = inspect.signature(TemplateEngine.__init__)
        assert "template_dir" in sig.parameters

    def test_template_engine_has_render(self):
        assert hasattr(TemplateEngine, "render")

    def test_template_engine_render_signature(self):
        sig = inspect.signature(TemplateEngine.render)
        assert "scenario" in sig.parameters
        assert "profile" in sig.parameters
        assert "context" in sig.parameters

    def test_template_engine_has_list_scenarios(self):
        assert hasattr(TemplateEngine, "list_scenarios")

    def test_template_engine_list_scenarios_return_annotation(self):
        sig = inspect.signature(TemplateEngine.list_scenarios)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_template_engine_has_render_system_prompt(self):
        assert hasattr(TemplateEngine, "render_system_prompt")

    def test_template_engine_render_system_prompt_signature(self):
        sig = inspect.signature(TemplateEngine.render_system_prompt)
        assert "profile" in sig.parameters
        assert "scenario" in sig.parameters


class TestMultiBrandInterface:
    """Verify the multi_brand module interface."""

    def test_voice_manager_importable(self):
        assert VoiceManager is not None

    def test_voice_manager_is_class(self):
        assert inspect.isclass(VoiceManager)

    def test_voice_manager_init_signature(self):
        sig = inspect.signature(VoiceManager.__init__)
        assert "profiles_dir" in sig.parameters

    def test_voice_manager_has_create_brand(self):
        assert hasattr(VoiceManager, "create_brand")

    def test_voice_manager_create_brand_signature(self):
        sig = inspect.signature(VoiceManager.create_brand)
        assert "name" in sig.parameters
        assert "profile" in sig.parameters

    def test_voice_manager_has_get_brand(self):
        assert hasattr(VoiceManager, "get_brand")

    def test_voice_manager_get_brand_signature(self):
        sig = inspect.signature(VoiceManager.get_brand)
        assert "brand_id" in sig.parameters

    def test_voice_manager_has_list_brands(self):
        assert hasattr(VoiceManager, "list_brands")

    def test_voice_manager_list_brands_return_annotation(self):
        sig = inspect.signature(VoiceManager.list_brands)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_voice_manager_has_delete_brand(self):
        assert hasattr(VoiceManager, "delete_brand")

    def test_voice_manager_delete_brand_signature(self):
        sig = inspect.signature(VoiceManager.delete_brand)
        assert "brand_id" in sig.parameters

    def test_voice_manager_has_set_active(self):
        assert hasattr(VoiceManager, "set_active")

    def test_voice_manager_set_active_signature(self):
        sig = inspect.signature(VoiceManager.set_active)
        assert "brand_id" in sig.parameters
        assert "scope" in sig.parameters

    def test_voice_manager_has_get_active(self):
        assert hasattr(VoiceManager, "get_active")

    def test_voice_manager_get_active_signature(self):
        sig = inspect.signature(VoiceManager.get_active)
        assert "scope" in sig.parameters

    def test_voice_manager_has_list_scopes(self):
        assert hasattr(VoiceManager, "list_scopes")


class TestPromptBindingInterface:
    """Verify the prompt_binding module interface."""

    def test_prompt_binder_importable(self):
        assert PromptBinder is not None

    def test_prompt_binder_is_class(self):
        assert inspect.isclass(PromptBinder)

    def test_prompt_binder_init_signature(self):
        sig = inspect.signature(PromptBinder.__init__)
        assert "template_engine" in sig.parameters
        assert "preset_manager" in sig.parameters

    def test_prompt_binder_has_create_prompt(self):
        assert hasattr(PromptBinder, "create_prompt")

    def test_prompt_binder_create_prompt_signature(self):
        sig = inspect.signature(PromptBinder.create_prompt)
        assert "content_type" in sig.parameters
        assert "profile" in sig.parameters
        assert "topic" in sig.parameters

    def test_prompt_binder_has_create_system_prompt(self):
        assert hasattr(PromptBinder, "create_system_prompt")

    def test_prompt_binder_has_list_content_types(self):
        assert hasattr(PromptBinder, "list_content_types")


class TestScopingInterface:
    """Verify the scoping module interface."""

    def test_voice_scope_importable(self):
        assert VoiceScope is not None

    def test_voice_scope_is_class(self):
        assert inspect.isclass(VoiceScope)

    def test_voice_scope_init_signature(self):
        sig = inspect.signature(VoiceScope.__init__)
        assert "config_dir" in sig.parameters

    def test_voice_scope_has_set_user_voice(self):
        assert hasattr(VoiceScope, "set_user_voice")

    def test_voice_scope_set_user_voice_signature(self):
        sig = inspect.signature(VoiceScope.set_user_voice)
        assert "user_id" in sig.parameters
        assert "brand_id" in sig.parameters

    def test_voice_scope_has_get_user_voice(self):
        assert hasattr(VoiceScope, "get_user_voice")

    def test_voice_scope_get_user_voice_signature(self):
        sig = inspect.signature(VoiceScope.get_user_voice)
        assert "user_id" in sig.parameters

    def test_voice_scope_has_set_project_voice(self):
        assert hasattr(VoiceScope, "set_project_voice")

    def test_voice_scope_set_project_voice_signature(self):
        sig = inspect.signature(VoiceScope.set_project_voice)
        assert "project_id" in sig.parameters
        assert "brand_id" in sig.parameters

    def test_voice_scope_has_get_project_voice(self):
        assert hasattr(VoiceScope, "get_project_voice")

    def test_voice_scope_has_resolve(self):
        assert hasattr(VoiceScope, "resolve")

    def test_voice_scope_resolve_signature(self):
        sig = inspect.signature(VoiceScope.resolve)
        assert "user_id" in sig.parameters
        assert "project_id" in sig.parameters

    def test_voice_scope_has_clear(self):
        assert hasattr(VoiceScope, "clear")

    def test_voice_scope_clear_signature(self):
        sig = inspect.signature(VoiceScope.clear)
        assert "scope" in sig.parameters
        assert "scope_id" in sig.parameters


class TestComplianceInterface:
    """Verify the compliance module interface."""

    def test_compliance_result_importable(self):
        assert ComplianceResult is not None

    def test_compliance_result_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ComplianceResult, BaseModel)

    def test_compliance_result_fields(self):
        sig = inspect.signature(ComplianceResult)
        assert "overall_score" in sig.parameters
        assert "vocabulary_score" in sig.parameters
        assert "readability_score" in sig.parameters
        assert "tone_score" in sig.parameters
        assert "banned_terms_found" in sig.parameters
        assert "violations" in sig.parameters

    def test_compliance_scorer_importable(self):
        assert ComplianceScorer is not None

    def test_compliance_scorer_is_class(self):
        assert inspect.isclass(ComplianceScorer)

    def test_compliance_scorer_init_signature(self):
        sig = inspect.signature(ComplianceScorer.__init__)
        assert "profile" in sig.parameters

    def test_compliance_scorer_has_score(self):
        assert hasattr(ComplianceScorer, "score")

    def test_compliance_scorer_score_signature(self):
        sig = inspect.signature(ComplianceScorer.score)
        assert "text" in sig.parameters

    def test_compliance_scorer_has_check_banned_terms(self):
        assert hasattr(ComplianceScorer, "check_banned_terms")

    def test_compliance_scorer_has_check_vocabulary(self):
        assert hasattr(ComplianceScorer, "check_vocabulary")

    def test_compliance_scorer_has_check_readability(self):
        assert hasattr(ComplianceScorer, "check_readability")


class TestExtractionInterface:
    """Verify the extraction module interface."""

    def test_voice_extractor_importable(self):
        assert VoiceExtractor is not None

    def test_voice_extractor_is_class(self):
        assert inspect.isclass(VoiceExtractor)

    def test_voice_extractor_init_signature(self):
        sig = inspect.signature(VoiceExtractor.__init__)
        assert "min_words" in sig.parameters

    def test_voice_extractor_init_min_words_default(self):
        sig = inspect.signature(VoiceExtractor.__init__)
        param = sig.parameters["min_words"]
        assert param.default is not inspect.Parameter.empty

    def test_voice_extractor_has_extract(self):
        assert hasattr(VoiceExtractor, "extract")

    def test_voice_extractor_extract_signature(self):
        sig = inspect.signature(VoiceExtractor.extract)
        assert "samples" in sig.parameters

    def test_voice_extractor_has_analyze_samples(self):
        assert hasattr(VoiceExtractor, "analyze_samples")

    def test_voice_extractor_analyze_samples_signature(self):
        sig = inspect.signature(VoiceExtractor.analyze_samples)
        assert "samples" in sig.parameters


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (should FAIL with NotImplementedError)
#
# These tests describe how the functions should behave once implemented.
# When run against stubs, they fail because the implementation raises
# NotImplementedError. This is the TDD "red" phase.
# ============================================================================


class TestParserBehavioral:
    """Behavioral tests for parser — should fail with NotImplementedError."""

    def test_parse_brand_voice_parses_file(self, tmp_path):
        """parse_brand_voice() should parse a valid BRAND_VOICE.md file."""
        md_file = tmp_path / "BRAND_VOICE.md"
        md_file.write_text(
            "# Identity\n"
            "who: Acme Corp\n"
            "audience: Developers\n"
            "purpose: Build great tools\n"
            "\n"
            "## Voice Attributes\n"
            "- formality: 0.7 (casual ↔ formal)\n"
            "\n"
            "## Vocabulary\n"
            "preferred: scalable, robust\n"
            "banned: pivot, synergy\n"
            "\n"
            "## Scenarios\n"
            "- incident: transparent\n"
            "\n"
            "## Formatting\n"
            "heading_style: sentence\n"
        )
        profile = parse_brand_voice(md_file)
        assert profile.name == "Acme Corp"

    def test_parse_brand_voice_string_parses(self):
        """parse_brand_voice_string() should parse markdown content."""
        content = (
            "# Identity\n"
            "who: Test Brand\n"
            "audience: QA Engineers\n"
            "purpose: Validate parsing\n"
            "## Voice Attributes\n"
            "- tone: 0.5 (serious ↔ playful)\n"
            "## Vocabulary\n"
            "preferred: quality, reliable\n"
            "banned: crash, bug\n"
            "## Scenarios\n"
            "- release: confident\n"
            "## Formatting\n"
            "heading_style: title\n"
        )
        profile = parse_brand_voice_string(content, source="test.md")
        assert profile is not None
        assert profile.metadata.get("source_file") == "test.md"

    def test_parse_brand_voice_file_not_found(self):
        """parse_brand_voice() should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_brand_voice("/nonexistent/BRAND_VOICE.md")

    def test_parse_brand_voice_missing_section(self, tmp_path):
        """parse_brand_voice() should raise ParseError for missing required section."""
        md_file = tmp_path / "incomplete.md"
        md_file.write_text("# Identity\nwho: Acme\n")
        with pytest.raises(ParseError):
            parse_brand_voice(md_file)

    def test_validate_brand_voice_valid_input(self):
        """validate_brand_voice() should return empty list for valid data."""
        valid = {
            "id": "test-v1",
            "name": "Test",
            "description": "Test",
            "attributes": [{"name": "tone", "min_label": "a", "max_label": "b", "value": 0.5}],
            "vocabulary": {"preferred": [], "banned": [], "jargon_level": "light"},
            "scenarios": [],
            "formatting": {"heading_style": "sentence", "bullet_style": "dash", "citation_format": "inline"},
        }
        errors = validate_brand_voice(valid)
        assert errors == []

    def test_validate_brand_voice_invalid_input(self):
        """validate_brand_voice() should return errors for invalid data."""
        errors = validate_brand_voice({})
        assert len(errors) > 0
        assert isinstance(errors[0], str)


class TestPresetsBehavioral:
    """Behavioral tests for PresetManager — should fail with NotImplementedError."""

    def test_preset_manager_init_creates_dir(self, temp_dir):
        """PresetManager should create custom_dir if it does not exist."""
        custom = temp_dir / "my_presets"
        mgr = PresetManager(custom_dir=custom)
        assert custom.exists()
        assert custom.is_dir()

    def test_preset_manager_list_builtins(self, temp_dir):
        """list_builtins() should return sorted built-in preset names."""
        mgr = PresetManager(temp_dir / "presets")
        names = mgr.list_builtins()
        assert isinstance(names, list)
        assert len(names) >= 5
        assert names == sorted(names)

    def test_preset_manager_get_preset_by_name(self, temp_dir):
        """get_preset() should return a VoiceProfile for a valid name."""
        mgr = PresetManager(temp_dir / "presets")
        profile = mgr.get_preset("formal")
        assert isinstance(profile, VoiceProfile)
        assert profile.name == "formal"

    def test_preset_manager_get_preset_not_found(self, temp_dir):
        """get_preset() should raise KeyError for unknown preset."""
        mgr = PresetManager(temp_dir / "presets")
        with pytest.raises(KeyError):
            mgr.get_preset("nonexistent")

    def test_preset_manager_save_and_list_custom(self, temp_dir, sample_voice_profile):
        """save_custom() should persist a profile, list_custom() should find it."""
        mgr = PresetManager(temp_dir / "presets")
        mgr.save_custom(sample_voice_profile, "my-brand")
        custom_names = mgr.list_custom()
        assert "my-brand" in custom_names

    def test_preset_manager_delete_custom(self, temp_dir, sample_voice_profile):
        """delete_custom() should remove a saved preset."""
        mgr = PresetManager(temp_dir / "presets")
        mgr.save_custom(sample_voice_profile, "to-delete")
        mgr.delete_custom("to-delete")
        assert "to-delete" not in mgr.list_custom()

    def test_preset_manager_delete_custom_not_found(self, temp_dir):
        """delete_custom() should raise KeyError for non-existent preset."""
        mgr = PresetManager(temp_dir / "presets")
        with pytest.raises(KeyError):
            mgr.delete_custom("ghost")

    def test_preset_manager_remix_creates_new(self, temp_dir):
        """remix() should produce a new profile without mutating the original."""
        mgr = PresetManager(temp_dir / "presets")
        original = mgr.get_preset("formal")
        remixed = mgr.remix("formal", {"name": "Formal Lite"})
        assert remixed is not original
        assert remixed.name == "Formal Lite"

    def test_preset_manager_custom_survives_reinit(self, temp_dir, sample_voice_profile):
        """Custom presets should persist across PresetManager instances."""
        mgr1 = PresetManager(temp_dir / "presets")
        mgr1.save_custom(sample_voice_profile, "persistent-brand")

        mgr2 = PresetManager(temp_dir / "presets")
        assert "persistent-brand" in mgr2.list_custom()


class TestTemplatesBehavioral:
    """Behavioral tests for TemplateEngine — should fail with NotImplementedError."""

    def test_template_engine_render(self, temp_dir, sample_voice_profile):
        """render() should produce a string with voice rules."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        result = engine.render("incident", sample_voice_profile)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_template_engine_render_with_context(self, temp_dir, sample_voice_profile):
        """render() should support additional context variables."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        result = engine.render("launch", sample_voice_profile, context={"product_name": "Acme Cloud"})
        assert "Acme Cloud" in result

    def test_template_engine_list_scenarios(self, temp_dir):
        """list_scenarios() should return 5+ built-in scenario names."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        scenarios = engine.list_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 5
        assert "incident" in scenarios

    def test_template_engine_render_missing_scenario(self, temp_dir, sample_voice_profile):
        """render() should raise KeyError for unknown scenario."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        with pytest.raises(KeyError):
            engine.render("unknown_scenario", sample_voice_profile)

    def test_template_engine_render_system_prompt(self, temp_dir, sample_voice_profile):
        """render_system_prompt() should produce a valid system prompt."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        prompt = engine.render_system_prompt(sample_voice_profile)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_template_engine_render_system_prompt_with_scenario(self, temp_dir, sample_voice_profile):
        """render_system_prompt() with scenario should append tone instructions."""
        engine = TemplateEngine(template_dir=temp_dir / "templates")
        generic = engine.render_system_prompt(sample_voice_profile)
        scoped = engine.render_system_prompt(sample_voice_profile, scenario="support_reply")
        assert scoped != generic
        assert len(scoped) > len(generic)


class TestMultiBrandBehavioral:
    """Behavioral tests for VoiceManager — should fail with NotImplementedError."""

    def test_voice_manager_create_and_get_brand(self, temp_dir, sample_voice_profile):
        """create_brand() should return an ID; get_brand() should retrieve it."""
        mgr = VoiceManager(temp_dir / "brands")
        brand_id = mgr.create_brand("Acme Corp", sample_voice_profile)
        assert isinstance(brand_id, str)
        assert len(brand_id) > 0

        retrieved = mgr.get_brand(brand_id)
        assert isinstance(retrieved, VoiceProfile)
        assert retrieved.id == sample_voice_profile.id

    def test_voice_manager_get_brand_not_found(self, temp_dir):
        """get_brand() should raise KeyError for unknown brand."""
        mgr = VoiceManager(temp_dir / "brands")
        with pytest.raises(KeyError):
            mgr.get_brand("nonexistent")

    def test_voice_manager_list_brands(self, temp_dir, sample_voice_profile):
        """list_brands() should return all registered brands."""
        mgr = VoiceManager(temp_dir / "brands")
        mgr.create_brand("Acme Corp", sample_voice_profile)
        brands = mgr.list_brands()
        assert isinstance(brands, dict)
        assert len(brands) >= 1

    def test_voice_manager_delete_brand(self, temp_dir, sample_voice_profile):
        """delete_brand() should remove a brand."""
        mgr = VoiceManager(temp_dir / "brands")
        brand_id = mgr.create_brand("To Delete", sample_voice_profile)
        mgr.delete_brand(brand_id)
        assert brand_id not in mgr.list_brands()

    def test_voice_manager_set_and_get_active_global(self, temp_dir, sample_voice_profile):
        """set_active('global') should set the global active brand."""
        mgr = VoiceManager(temp_dir / "brands")
        brand_id = mgr.create_brand("Global", sample_voice_profile)
        mgr.set_active(brand_id, scope="global")
        active = mgr.get_active(scope="global")
        assert active is not None
        assert active.id == sample_voice_profile.id

    def test_voice_manager_scopes_isolated(self, temp_dir, sample_voice_profile):
        """Setting active in one scope should not affect another."""
        mgr = VoiceManager(temp_dir / "brands")
        id1 = mgr.create_brand("Brand A", sample_voice_profile)
        mgr.set_active(id1, scope="global")
        # Project scope should be independent
        active_project = mgr.get_active(scope="project-x")
        assert active_project is None or active_project.id != id1

    def test_voice_manager_get_active_none(self, temp_dir):
        """get_active() should return None when no brand is active."""
        mgr = VoiceManager(temp_dir / "brands")
        active = mgr.get_active(scope="global")
        assert active is None

    def test_voice_manager_list_scopes(self, temp_dir, sample_voice_profile):
        """list_scopes() should show active brand assignments."""
        mgr = VoiceManager(temp_dir / "brands")
        brand_id = mgr.create_brand("Test", sample_voice_profile)
        mgr.set_active(brand_id, scope="project-alpha")
        scopes = mgr.list_scopes()
        assert isinstance(scopes, dict)
        assert "project-alpha" in scopes

    def test_voice_manager_delete_active_brand_clears_scope(self, temp_dir, sample_voice_profile):
        """Deleting an active brand should clear it from its scope."""
        mgr = VoiceManager(temp_dir / "brands")
        brand_id = mgr.create_brand("Active Brand", sample_voice_profile)
        mgr.set_active(brand_id, scope="global")
        mgr.delete_brand(brand_id)
        assert mgr.get_active(scope="global") is None


class TestPromptBindingBehavioral:
    """Behavioral tests for PromptBinder — should fail with NotImplementedError."""

    def test_prompt_binder_create_prompt(self, temp_dir, sample_voice_profile):
        """create_prompt() should return a complete prompt string."""
        engine = TemplateEngine.__new__(TemplateEngine)
        # Monkey-patch to avoid NotImplementedError for template engine
        binder = PromptBinder(engine)
        prompt = binder.create_prompt("email", sample_voice_profile, "New Feature Launch")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_prompt_binder_create_prompt_with_kwargs(self, temp_dir, sample_voice_profile):
        """create_prompt() should support additional kwargs."""
        binder = PromptBinder(TemplateEngine.__new__(TemplateEngine))
        prompt = binder.create_prompt(
            "landing_page",
            sample_voice_profile,
            "Cloud Platform",
            audience="CTOs",
            length="short",
        )
        assert "CTOs" in prompt

    def test_prompt_binder_create_system_prompt(self, sample_voice_profile):
        """create_system_prompt() should include voice rules."""
        binder = PromptBinder(TemplateEngine.__new__(TemplateEngine))
        result = binder.create_system_prompt(sample_voice_profile)
        assert isinstance(result, str)
        assert "brand" in result.lower()

    def test_prompt_binder_create_system_prompt_with_type(self, sample_voice_profile):
        """create_system_prompt() with content_type should add type-specific rules."""
        binder = PromptBinder(TemplateEngine.__new__(TemplateEngine))
        result = binder.create_system_prompt(sample_voice_profile, content_type="email")
        assert "email" in result.lower()

    def test_prompt_binder_list_content_types(self):
        """list_content_types() should return available types."""
        binder = PromptBinder(TemplateEngine.__new__(TemplateEngine))
        types = binder.list_content_types()
        assert isinstance(types, list)
        assert "email" in types


class TestScopingBehavioral:
    """Behavioral tests for VoiceScope — should fail with NotImplementedError."""

    def test_voice_scope_set_and_get_user_voice(self, temp_dir):
        """User voice should persist within the same scope manager."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_user_voice("user-1", "brand-42")
        result = scope.get_user_voice("user-1")
        assert result == "brand-42"

    def test_voice_scope_get_user_voice_not_set(self, temp_dir):
        """get_user_voice() should return None for unknown user."""
        scope = VoiceScope(temp_dir / "config")
        result = scope.get_user_voice("unknown-user")
        assert result is None

    def test_voice_scope_set_and_get_project_voice(self, temp_dir):
        """Project voice should persist within the same scope manager."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_project_voice("project-1", "brand-99")
        result = scope.get_project_voice("project-1")
        assert result == "brand-99"

    def test_voice_scope_resolve_project_overrides_user(self, temp_dir):
        """resolve() should return project voice when both are set."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_user_voice("user-1", "brand-user")
        scope.set_project_voice("project-1", "brand-project")
        result = scope.resolve("user-1", "project-1")
        assert result == "brand-project"

    def test_voice_scope_resolve_falls_back_to_user(self, temp_dir):
        """resolve() should fall back to user voice when project not set."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_user_voice("user-1", "brand-user")
        result = scope.resolve("user-1", "project-without-voice")
        assert result == "brand-user"

    def test_voice_scope_resolve_returns_none(self, temp_dir):
        """resolve() should return None when no voice is configured."""
        scope = VoiceScope(temp_dir / "config")
        result = scope.resolve("lonely-user")
        assert result is None

    def test_voice_scope_clear_user_voice(self, temp_dir):
        """clear() should remove user voice binding."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_user_voice("user-1", "brand-42")
        scope.clear("user", "user-1")
        assert scope.get_user_voice("user-1") is None

    def test_voice_scope_clear_project_voice(self, temp_dir):
        """clear() should remove project voice binding."""
        scope = VoiceScope(temp_dir / "config")
        scope.set_project_voice("project-1", "brand-99")
        scope.clear("project", "project-1")
        assert scope.get_project_voice("project-1") is None

    def test_voice_scope_config_dir_created(self, temp_dir):
        """Config directory should be created if it does not exist."""
        nested = temp_dir / "deep" / "nested" / "config"
        scope = VoiceScope(nested)
        assert nested.exists()
        assert nested.is_dir()


class TestComplianceBehavioral:
    """Behavioral tests for ComplianceScorer — should fail with NotImplementedError."""

    def test_compliance_scorer_score_returns_result(self, sample_voice_profile, sample_text):
        """score() should return a ComplianceResult."""
        scorer = ComplianceScorer(sample_voice_profile)
        result = scorer.score(sample_text)
        assert isinstance(result, ComplianceResult)
        assert 0.0 <= result.overall_score <= 1.0

    def test_compliance_scorer_score_perfect_text(self, sample_voice_profile):
        """Perfectly compliant text should score 1.0."""
        scorer = ComplianceScorer(sample_voice_profile)
        perfect = "We offer scalable and robust solutions for enterprise teams."
        result = scorer.score(perfect)
        assert result.overall_score == 1.0
        assert result.violations == []

    def test_compliance_scorer_check_banned_terms(self, sample_voice_profile, sample_text_with_banned_terms):
        """check_banned_terms() should find banned terms."""
        scorer = ComplianceScorer(sample_voice_profile)
        found = scorer.check_banned_terms(sample_text_with_banned_terms)
        assert isinstance(found, list)
        assert "pivot" in found or "synergy" in found or "disrupt" in found

    def test_compliance_scorer_check_banned_terms_clean(self, sample_voice_profile, sample_text):
        """check_banned_terms() should return empty list for clean text."""
        scorer = ComplianceScorer(sample_voice_profile)
        found = scorer.check_banned_terms(sample_text)
        assert found == []

    def test_compliance_scorer_check_vocabulary(self, sample_voice_profile, sample_text):
        """check_vocabulary() should return vocabulary analysis."""
        scorer = ComplianceScorer(sample_voice_profile)
        analysis = scorer.check_vocabulary(sample_text)
        assert isinstance(analysis, dict)
        assert "preferred_ratio" in analysis or "banned_ratio" in analysis

    def test_compliance_scorer_check_readability(self, sample_voice_profile, sample_text):
        """check_readability() should return a float score."""
        scorer = ComplianceScorer(sample_voice_profile)
        score = scorer.check_readability(sample_text)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_compliance_scorer_low_score_for_violations(self, sample_voice_profile, sample_text_with_banned_terms):
        """Text with banned terms should score lower than clean text."""
        scorer = ComplianceScorer(sample_voice_profile)
        bad_result = scorer.score(sample_text_with_banned_terms)
        assert bad_result.overall_score < 0.5
        assert len(bad_result.violations) > 0


class TestExtractionBehavioral:
    """Behavioral tests for VoiceExtractor — should fail with NotImplementedError."""

    def test_voice_extractor_extract_returns_profile(self):
        """extract() should return a valid VoiceProfile."""
        extractor = VoiceExtractor(min_words=100)
        samples = [
            "We are excited to announce our new platform. "
            "This solution helps teams collaborate more effectively across departments. "
            "Our mission is to make work easier for everyone involved in the process."
        ]
        profile = extractor.extract(samples)
        assert isinstance(profile, VoiceProfile)
        assert len(profile.id) > 0
        assert len(profile.name) > 0
        assert len(profile.description) > 0

    def test_voice_extractor_extract_infers_vocabulary(self):
        """extract() should infer vocabulary rules from samples."""
        extractor = VoiceExtractor(min_words=50)
        samples = [
            "Our scalable and robust platform helps enterprise teams. "
            "We provide proven solutions for modern businesses."
        ]
        profile = extractor.extract(samples)
        assert len(profile.vocabulary.preferred) > 0

    def test_voice_extractor_extract_raises_below_min_words(self):
        """extract() should raise ValueError for too few words."""
        extractor = VoiceExtractor(min_words=1000)
        with pytest.raises(ValueError):
            extractor.extract(["Too short"])

    def test_voice_extractor_analyze_samples(self):
        """analyze_samples() should return analysis metrics."""
        extractor = VoiceExtractor(min_words=50)
        samples = [
            "We are pleased to announce a new feature release. "
            "This update includes performance improvements and bug fixes."
        ]
        analysis = extractor.analyze_samples(samples)
        assert isinstance(analysis, dict)
        assert len(analysis) > 0
