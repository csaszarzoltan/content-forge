"""Interface and behavioral tests for per-language prompt template registry.

Interface tests  - verify imports, class signatures (should PASS).
Behavioral tests - verify NotImplementedError for stubs.

AC-T5 reference: Per-Language Prompt Templates (P1 - Brand Integrity).
"""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest


# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.services.prompt_templates import (
    LanguagePromptTemplate,
    PromptTemplateRegistry,
    TemplateInfo,
)


# ===========================================================================
# SECTION 1 - INTERFACE TESTS (should PASS immediately)
# ===========================================================================


class TestLanguagePromptTemplateInterface:
    """Verify the LanguagePromptTemplate schema interface.

    AC-T5.2: Schema fields must exist with correct types.
    """

    def test_importable(self):
        assert LanguagePromptTemplate is not None

    def test_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(LanguagePromptTemplate, BaseModel)

    def test_language_code_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "language_code" in sig.parameters
        assert sig.parameters["language_code"].annotation is str

    def test_content_type_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "content_type" in sig.parameters

    def test_system_prompt_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "system_prompt" in sig.parameters

    def test_user_prompt_template_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "user_prompt_template" in sig.parameters

    def test_brand_voice_translation_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "brand_voice_translation" in sig.parameters

    def test_brand_voice_translation_optional(self):
        """brand_voice_translation defaults to None (AC-T5.5)."""
        tpl = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Test {brand_voice_context}",
            user_prompt_template="Test {topic}",
        )
        assert tpl.brand_voice_translation is None

    def test_character_budget_warning_field(self):
        sig = inspect.signature(LanguagePromptTemplate)
        assert "character_budget_warning" in sig.parameters

    def test_character_budget_warning_default_false(self):
        tpl = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Test {brand_voice_context}",
            user_prompt_template="Test {topic}",
        )
        assert tpl.character_budget_warning is False

    def test_character_budget_warning_true_for_high_token_languages(self):
        tpl = LanguagePromptTemplate(
            language_code="ja",
            content_type="email",
            system_prompt="Test",
            user_prompt_template="Test",
            character_budget_warning=True,
        )
        assert tpl.character_budget_warning is True


class TestTemplateInfoInterface:
    """Verify the TemplateInfo summary schema."""

    def test_importable(self):
        assert TemplateInfo is not None

    def test_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(TemplateInfo, BaseModel)

    def test_template_info_fields(self):
        sig = inspect.signature(TemplateInfo)
        assert "language_code" in sig.parameters
        assert "content_type" in sig.parameters
        assert "character_budget_warning" in sig.parameters


class TestPromptTemplateRegistryInterface:
    """Verify the PromptTemplateRegistry class interface.

    AC-T5.1: CRUD methods must exist with correct signatures.
    """

    def test_importable(self):
        assert PromptTemplateRegistry is not None

    def test_is_class(self):
        assert inspect.isclass(PromptTemplateRegistry)

    def test_get_template_signature(self):
        assert callable(PromptTemplateRegistry.get_template)
        sig = inspect.signature(PromptTemplateRegistry.get_template)
        params = {"language", "content_type"}
        assert params.issubset(sig.parameters)

    def test_register_template_signature(self):
        assert callable(PromptTemplateRegistry.register_template)
        sig = inspect.signature(PromptTemplateRegistry.register_template)
        assert "template" in sig.parameters

    def test_list_templates_signature(self):
        assert callable(PromptTemplateRegistry.list_templates)

    def test_load_from_directory_signature(self):
        assert callable(PromptTemplateRegistry.load_from_directory)
        sig = inspect.signature(PromptTemplateRegistry.load_from_directory)
        assert "path" in sig.parameters

    def test_clear_method(self):
        assert callable(PromptTemplateRegistry.clear)

    def test_constructor_takes_no_args(self):
        """Registry __init__ takes only self."""
        sig = inspect.signature(PromptTemplateRegistry.__init__)
        keys = list(sig.parameters.keys())
        assert keys == ["self"] or (len(keys) == 1 and keys[0] == "self")


# ===========================================================================
# SECTION 2 - BEHAVIORAL TESTS (verify NotImplementedError stubs)
# ===========================================================================


class TestPromptTemplateRegistryBehavioral:
    """Behavioral tests for PromptTemplateRegistry."""

    def test_registry_constructs(self):
        registry = PromptTemplateRegistry()
        assert registry is not None

    def test_get_template_returns_template(self):
        """AC-T5.1: get_template returns English default template."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("en", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        assert result.language_code == "en"
        assert result.content_type == "blog"

    def test_register_template_stores_it(self):
        """AC-T5.1: register_template stores a template for retrieval."""
        registry = PromptTemplateRegistry()
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Du bist ein Experte. {brand_voice_context}",
            user_prompt_template="Schreibe uber {topic}",
        )
        registry.register_template(template)
        result = registry.get_template("de", "blog")
        assert result is template

    def test_list_templates_returns_list(self):
        """AC-T5.1: list_templates returns a list of TemplateInfo."""
        registry = PromptTemplateRegistry()
        result = registry.list_templates()
        assert isinstance(result, list)
        # English defaults produce 3 templates
        assert len(result) >= 3
        assert all(isinstance(t, TemplateInfo) for t in result)

    def test_load_from_directory_raises_filenotfound(self):
        """AC-T5.6: load_from_directory raises FileNotFoundError for missing dir."""
        registry = PromptTemplateRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_from_directory("/tmp/templates")

    def test_create_defaults_populates_english(self):
        """AC-T5.1: _create_defaults populates English default templates."""
        registry = PromptTemplateRegistry()
        registry._create_defaults()
        # Should still have at least the English defaults
        assert len(registry.list_templates()) >= 3

    def test_clear_works_after_construction(self):
        """clear() should empty the store without error."""
        registry = PromptTemplateRegistry()
        registry.clear()
        assert len(registry.list_templates()) == 0


# ===========================================================================
# SECTION 3 - BEHAVIORAL TESTS - Template Selection (AC-T5.3, AC-T5.4)
# ===========================================================================


class TestTemplateSelectionBehavioral:
    """Template selection and fallback chain.

    AC-T5.3: Auto template selection based on language + content_type.
    AC-T5.4: Fallback chain (language -> English -> error).
    """

    def test_auto_selection_by_language(self):
        """AC-T5.3: get_template should match on language + content_type."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("en", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        assert result.language_code == "en"

    def test_auto_selection_by_content_type(self):
        """AC-T5.3: get_template should differentiate by content_type."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("en", "social")
        assert isinstance(result, LanguagePromptTemplate)
        assert result.content_type == "social"

    def test_fallback_to_english(self):
        """AC-T5.4: Missing language falls back to English template."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("hu", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        # Fallback adds 'Respond in hu' instruction
        assert "Respond in hu" in result.system_prompt

    def test_fallback_to_english_for_unknown_language(self):
        """AC-T5.4: Unknown language code still falls back."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("xx", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        # Should fall back to English with instruction
        assert "Respond in xx" in result.system_prompt

    def test_fallback_exhausted_raises_keyerror(self):
        """AC-T5.4: Missing lang + unknown content_type raises KeyError."""
        registry = PromptTemplateRegistry()
        with pytest.raises(KeyError):
            registry.get_template("hu", "podcast")

    def test_english_template_selected_directly(self):
        """English templates should be selectable without fallback."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("en", "email")
        assert isinstance(result, LanguagePromptTemplate)
        assert result.language_code == "en"
        assert result.content_type == "email"


# ===========================================================================
# SECTION 4 - BEHAVIORAL TESTS - CRUD Operations (AC-T5.1)
# ===========================================================================


class TestTemplateCRUDBehavioral:
    """Template registry CRUD operations.

    AC-T5.1: Full CRUD lifecycle.
    """

    def test_register_and_get_template(self):
        """Register a template, then retrieve it."""
        registry = PromptTemplateRegistry()
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Deutsch: {brand_voice_context}",
            user_prompt_template="Schreibe {topic}",
            brand_voice_translation={"tone": "professionell"},
        )
        registry.register_template(template)
        retrieved = registry.get_template("de", "blog")
        assert retrieved is template
        assert retrieved.language_code == "de"
        assert retrieved.content_type == "blog"
        assert retrieved.brand_voice_translation == {"tone": "professionell"}

    def test_register_overwrites_existing(self):
        """Registering same (language, content_type) overwrites."""
        registry = PromptTemplateRegistry()
        t1 = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="V1",
            user_prompt_template="V1",
        )
        t2 = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="V2",
            user_prompt_template="V2",
        )
        registry.register_template(t1)
        registry.register_template(t2)
        retrieved = registry.get_template("de", "blog")
        assert retrieved.system_prompt == "V2"

    def test_list_templates_returns_all(self):
        """list_templates should return all registered templates."""
        registry = PromptTemplateRegistry()
        result = registry.list_templates()
        assert isinstance(result, list)
        # Should include English defaults plus any we add
        for item in result:
            assert isinstance(item, TemplateInfo)


# ===========================================================================
# SECTION 5 - BEHAVIORAL TESTS - Brand Voice Translation (AC-T5.5)
# ===========================================================================


class TestBrandVoiceTranslationBehavioral:
    """Brand voice attribute translation injection.

    AC-T5.5: Brand voice attributes are translated when
    brand_voice_translation dict is provided.
    """

    def test_brand_voice_translation_in_system_prompt(self):
        """Translated attributes should be injectable into system prompt."""
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Markenstimme: {brand_voice_context}",
            user_prompt_template="Thema: {topic}",
            brand_voice_translation={
                "formality": "formell",
                "enthusiasm": "Begeisterung",
            },
        )
        assert template.brand_voice_translation is not None
        assert "formality" in template.brand_voice_translation

    def test_brand_voice_translation_default_none(self):
        """Without brand_voice_translation, it should be None."""
        template = LanguagePromptTemplate(
            language_code="en",
            content_type="blog",
            system_prompt="You are a writer. {brand_voice_context}",
            user_prompt_template="Write about {topic}",
        )
        assert template.brand_voice_translation is None

    def test_translation_injected_into_generated_prompt(self):
        """When brand_voice_translation is set, prompt should use it."""
        registry = PromptTemplateRegistry()
        # Register a German template with translation
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Markenstimme: {brand_voice_context}",
            user_prompt_template="Thema: {topic}",
            brand_voice_translation={
                "formality": "formell",
                "enthusiasm": "Begeisterung",
            },
        )
        registry.register_template(template)
        result = registry.get_template("de", "blog")
        assert result.brand_voice_translation is not None
        assert "formality" in result.brand_voice_translation
        assert result.brand_voice_translation["formality"] == "formell"


# ===========================================================================
# SECTION 6 - BEHAVIORAL TESTS - File Loading (AC-T5.6)
# ===========================================================================


class TestFileLoadingBehavioral:
    """File-based template loading at startup.

    AC-T5.6: Templates stored as JSON/YAML files in
    src/brand_voice/templates/ and loaded at startup.
    """

    def test_load_from_templates_directory(self):
        """Load template files from src/brand_voice/templates/."""
        registry = PromptTemplateRegistry()
        registry.clear()
        template_dir = Path("src/brand_voice/templates")
        count = registry.load_from_directory(str(template_dir))
        assert count > 0

    def test_load_count_returned(self):
        """load_from_directory should return the count of loaded templates."""
        registry = PromptTemplateRegistry()
        registry.clear()
        template_dir = Path("src/brand_voice/templates")
        count = registry.load_from_directory(str(template_dir))
        assert count == 3  # de_blog.json, fr_social.json, ja_email.json
        assert isinstance(count, int)

    def test_loaded_templates_are_accessible(self):
        """After loading, templates should be accessible via get_template."""
        registry = PromptTemplateRegistry()
        registry.clear()
        template_dir = Path("src/brand_voice/templates")
        count = registry.load_from_directory(str(template_dir))
        assert count > 0
        result = registry.get_template("de", "blog")
        assert result is not None
        assert result.language_code == "de"

    def test_load_nonexistent_directory_raises_error(self):
        """Loading from non-existent dir raises FileNotFoundError."""
        registry = PromptTemplateRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_from_directory("/nonexistent/path")


# ===========================================================================
# SECTION 7 - BEHAVIORAL TESTS - Placeholder Interpolation
# ===========================================================================


class TestPlaceholderInterpolationBehavioral:
    """Template placeholder interpolation."""

    def test_system_prompt_has_brand_voice_placeholder(self):
        """System prompt should include {brand_voice_context}."""
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Du bist ein Autor. {brand_voice_context}",
            user_prompt_template="Schreibe: {topic}",
        )
        assert "{brand_voice_context}" in template.system_prompt

    def test_user_prompt_has_topic_placeholder(self):
        """User prompt should include {topic} placeholder."""
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="System: {brand_voice_context}",
            user_prompt_template="Thema: {topic}\nPublikum: {audience}\nLange: {length}",
        )
        assert "{topic}" in template.user_prompt_template
        assert "{audience}" in template.user_prompt_template
        assert "{length}" in template.user_prompt_template

    def test_format_user_prompt_with_values(self):
        """User prompt should be formatable with actual values."""
        template = LanguagePromptTemplate(
            language_code="en",
            content_type="blog",
            system_prompt="System prompt",
            user_prompt_template="Write about {topic} for {audience}",
        )
        result = template.user_prompt_template.format(
            topic="AI Trends",
            audience="developers",
        )
        assert "AI Trends" in result
        assert "developers" in result

    def test_format_system_prompt_with_brand_voice(self):
        """System prompt should accept brand_voice_context formatting."""
        template = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="Du bist {brand_voice_context}",
            user_prompt_template="{topic}",
        )
        result = template.system_prompt.format(
            brand_voice_context="ein professioneller deutscher Texter",
        )
        assert "deutscher Texter" in result


# ===========================================================================
# SECTION 8 - INTEGRATION TESTS
# ===========================================================================


class TestPromptTemplateIntegration:
    """Integration tests combining multiple AC-T5 requirements."""

    def test_full_crud_lifecycle(self):
        """AC-T5.1: Full CRUD lifecycle: register, list, get."""
        registry = PromptTemplateRegistry()
        registry.clear()  # start clean
        templates = [
            LanguagePromptTemplate(
                language_code="de",
                content_type="blog",
                system_prompt="DE Blog {brand_voice_context}",
                user_prompt_template="DE: {topic}",
            ),
            LanguagePromptTemplate(
                language_code="fr",
                content_type="social",
                system_prompt="FR Social {brand_voice_context}",
                user_prompt_template="FR: {topic}",
            ),
        ]
        for t in templates:
            registry.register_template(t)
        listing = registry.list_templates()
        assert len(listing) == 2
        for t in templates:
            retrieved = registry.get_template(t.language_code, t.content_type)
            assert retrieved.language_code == t.language_code
            assert retrieved.content_type == t.content_type

    def test_fallback_uses_english_template(self):
        """AC-T5.4: Fallback returns English template with instruction."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("hu", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        # Fallback should include language instruction
        assert "Respond in hu" in result.system_prompt

    def test_language_specific_preferred_over_english(self):
        """AC-T5.3: Language-specific template preferred over fallback."""
        registry = PromptTemplateRegistry()
        de_blog = LanguagePromptTemplate(
            language_code="de",
            content_type="blog",
            system_prompt="DE System: {brand_voice_context}",
            user_prompt_template="DE: {topic}",
        )
        registry.register_template(de_blog)
        result = registry.get_template("de", "blog")
        assert result.system_prompt.startswith("DE")

    def test_load_then_select(self):
        """AC-T5.3 + AC-T5.6: Load from files then select template."""
        registry = PromptTemplateRegistry()
        registry.clear()
        template_dir = Path("src/brand_voice/templates")
        count = registry.load_from_directory(str(template_dir))
        assert count > 0
        de_blog = registry.get_template("de", "blog")
        assert de_blog.language_code == "de"
        assert de_blog.content_type == "blog"

    def test_list_after_load_reflects_loaded_templates(self):
        """AC-T5.6: list_templates reflects loaded templates."""
        registry = PromptTemplateRegistry()
        registry.clear()
        template_dir = Path("src/brand_voice/templates")
        count = registry.load_from_directory(str(template_dir))
        assert count > 0
        listing = registry.list_templates()
        assert len(listing) == count

    def test_template_without_brand_voice_translation(self):
        """AC-T5.5: Template may omit brand_voice_translation (None)."""
        template = LanguagePromptTemplate(
            language_code="en",
            content_type="blog",
            system_prompt="You are a writer. {brand_voice_context}",
            user_prompt_template="Write about {topic} for {audience}",
        )
        assert template.brand_voice_translation is None
        user_prompt = template.user_prompt_template.format(
            topic="Testing", audience="developers"
        )
        assert "Testing" in user_prompt

    def test_japanese_character_budget_warning(self):
        """AC-T5.2: Japanese template flags character_budget_warning."""
        template = LanguagePromptTemplate(
            language_code="ja",
            content_type="blog",
            system_prompt="{brand_voice_context}",
            user_prompt_template="{topic}",
            character_budget_warning=True,
        )
        assert template.character_budget_warning is True
        assert "{brand_voice_context}" in template.system_prompt


# ===========================================================================
# SECTION 9 - EDGE CASE TESTS
# ===========================================================================


class TestPromptTemplateEdgeCases:
    """Edge cases for template registry.

    Unknown language, unknown content_type, empty templates,
    duplicate registrations.
    """

    def test_unknown_language_falls_back_to_english(self):
        """Unknown language falls back to English template (if content_type exists)."""
        registry = PromptTemplateRegistry()
        result = registry.get_template("elvish", "blog")
        assert isinstance(result, LanguagePromptTemplate)
        # Falls back to English with instruction
        assert "Respond in elvish" in result.system_prompt

    def test_unknown_content_type_raises_keyerror(self):
        """Unknown content_type triggers error even for English."""
        registry = PromptTemplateRegistry()
        with pytest.raises(KeyError):
            registry.get_template("en", "podcast")

    def test_language_code_case_sensitivity(self):
        """Language codes stored as-is; get_template normalizes to lowercase."""
        registry = PromptTemplateRegistry()
        template = LanguagePromptTemplate(
            language_code="DE",
            content_type="blog",
            system_prompt="DE System",
            user_prompt_template="DE topic",
        )
        registry.register_template(template)
        # get_template normalizes "de" -> "de", so ("de", "blog") != ("DE", "blog")
        # Falls back to English default
        result = registry.get_template("de", "blog")
        assert result.language_code == "en"  # English fallback, not the DE template

    def test_register_invalid_template_missing_fields(self):
        """Pydantic should enforce required fields."""
        with pytest.raises(Exception):
            LanguagePromptTemplate()  # type: ignore[call-arg]

    def test_clear_then_list_is_empty(self):
        """After clear, list_templates returns empty list."""
        registry = PromptTemplateRegistry()
        registry.clear()
        result = registry.list_templates()
        assert len(result) == 0

    def test_multiple_templates_same_language_different_types(self):
        """Same language, different content_types should coexist."""
        registry = PromptTemplateRegistry()
        blog = registry.get_template("en", "blog")
        social = registry.get_template("en", "social")
        email = registry.get_template("en", "email")
        assert isinstance(blog, LanguagePromptTemplate)
        assert isinstance(social, LanguagePromptTemplate)
        assert isinstance(email, LanguagePromptTemplate)
        assert blog.content_type == "blog"
        assert social.content_type == "social"
        assert email.content_type == "email"
