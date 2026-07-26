"""Tests for SEO readability scoring service."""
from __future__ import annotations

import inspect

import pytest

from src.schemas.seo import ReadabilityMetrics
from src.services.readability import ReadabilityScorer

pytestmark = pytest.mark.asyncio


# ── SECTION 1: Interface Tests ──────────────────────────────────────────────


class TestReadabilityScorerInterface:
    """Verify the ReadabilityScorer class interface contract."""

    def test_importable(self) -> None:
        assert ReadabilityScorer is not None

    def test_is_class(self) -> None:
        assert inspect.isclass(ReadabilityScorer)

    def test_init_exists(self) -> None:
        assert hasattr(ReadabilityScorer, "__init__")

    def test_init_signature(self) -> None:
        sig = inspect.signature(ReadabilityScorer.__init__)
        params = list(sig.parameters.keys())
        assert params == ["self"]

    def test_flesch_kincaid_exists(self) -> None:
        assert hasattr(ReadabilityScorer, "flesch_kincaid")

    def test_coleman_liau_exists(self) -> None:
        assert hasattr(ReadabilityScorer, "coleman_liau")

    def test_flesch_reading_ease_exists(self) -> None:
        assert hasattr(ReadabilityScorer, "flesch_reading_ease")

    def test_readability_metrics_exists(self) -> None:
        assert hasattr(ReadabilityScorer, "readability_metrics")

    def test_methods_are_sync(self) -> None:
        scorer = ReadabilityScorer()
        for name in ("flesch_kincaid", "coleman_liau", "flesch_reading_ease", "readability_metrics"):
            method = getattr(scorer, name)
            assert not inspect.iscoroutinefunction(method), f"{name} should be sync"

    def test_flesch_kincaid_signature(self) -> None:
        sig = inspect.signature(ReadabilityScorer.flesch_kincaid)
        params = list(sig.parameters.keys())
        assert params == ["self", "text"]

    def test_coleman_liau_signature(self) -> None:
        sig = inspect.signature(ReadabilityScorer.coleman_liau)
        params = list(sig.parameters.keys())
        assert params == ["self", "text"]

    def test_flesch_reading_ease_signature(self) -> None:
        sig = inspect.signature(ReadabilityScorer.flesch_reading_ease)
        params = list(sig.parameters.keys())
        assert params == ["self", "text"]

    def test_readability_metrics_signature(self) -> None:
        sig = inspect.signature(ReadabilityScorer.readability_metrics)
        params = list(sig.parameters.keys())
        assert params == ["self", "text"]


class TestReadabilityMetricsInterface:
    """Verify ReadabilityMetrics schema interface."""

    def test_importable(self) -> None:
        assert ReadabilityMetrics is not None

    def test_is_pydantic_model(self) -> None:
        assert hasattr(ReadabilityMetrics, "model_fields")

    def test_has_expected_fields(self) -> None:
        fields = set(ReadabilityMetrics.model_fields.keys())
        expected = {"flesch_kincaid", "coleman_liau", "flesch_reading_ease", "reading_level"}
        assert expected.issubset(fields)


# ── SECTION 2: Behavioral Tests ─────────────────────────────────────────────


class TestReadabilityScorerBehavior:
    """Behavioral tests using real textstat scoring."""

    def setup_method(self) -> None:
        self.scorer = ReadabilityScorer()

    def test_empty_text_flesch_kincaid_returns_zero(self) -> None:
        assert self.scorer.flesch_kincaid("") == 0.0

    def test_empty_text_coleman_liau_returns_zero(self) -> None:
        assert self.scorer.coleman_liau("") == 0.0

    def test_empty_text_flesch_reading_ease_returns_zero(self) -> None:
        assert self.scorer.flesch_reading_ease("") == 0.0

    def test_empty_text_readability_metrics_defaults(self) -> None:
        metrics = self.scorer.readability_metrics("")
        assert metrics.flesch_kincaid == 0.0
        assert metrics.coleman_liau == 0.0
        assert metrics.flesch_reading_ease == 0.0
        assert metrics.reading_level == "unknown"

    def test_basic_simple_text_returns_float(self) -> None:
        text = "The cat sat on the mat. The dog ran in the park."
        fk = self.scorer.flesch_kincaid(text)
        assert isinstance(fk, float)

    def test_basic_simple_text_returns_readability_metrics(self) -> None:
        text = "The cat sat on the mat. The dog ran in the park."
        metrics = self.scorer.readability_metrics(text)
        assert isinstance(metrics, ReadabilityMetrics)

    def test_easy_reading_level(self) -> None:
        # Very simple children's text should score FRE >= 80
        text = (
            "The cat sat on the mat. The dog ran in the park. "
            "A big red ball rolled down the hill. "
            "The sun is hot and bright today. "
            "I like to play with my friends. "
            "We run and jump and laugh a lot. "
            "The birds sing in the trees. "
            "My mom made cookies for me. "
            "They taste really good. "
            "I love to read books at night. "
            "The moon is big and round. "
            "I have a pet fish. His name is Goldie. "
            "He lives in a bowl. I feed him every day. "
            "We go to the park on sunny days. "
            "My dad pushes me on the swing. "
            "The ice cream man sells cold treats."
        )
        metrics = self.scorer.readability_metrics(text)
        assert metrics.flesch_reading_ease >= 80
        assert metrics.reading_level == "easy"

    def test_standard_reading_level(self) -> None:
        # News-like text should score FRE between 60-80
        text = (
            "Many people enjoy reading books in their free time. "
            "It is a good way to learn new things and relax. "
            "Some prefer fiction while others like non-fiction books. "
            "Libraries offer a wide selection for all ages. "
            "Reading every day can improve your vocabulary and writing skills. "
            "Children who read regularly tend to do better in school. "
            "Parents often read stories to their kids before bed. "
            "Book clubs are popular social activities in many communities."
        )
        metrics = self.scorer.readability_metrics(text)
        assert 60 <= metrics.flesch_reading_ease < 80
        assert metrics.reading_level == "standard"

    def test_difficult_reading_level(self) -> None:
        # Moderately complex text should score FRE between 40-60
        text = (
            "The history of the internet began in the 1960s with research networks. "
            "Early computers were large and expensive machines used by universities. "
            "The development of packet switching was a key breakthrough. "
            "Tim Berners-Lee invented the World Wide Web in 1989. "
            "This made it easier to share information across the network. "
            "Web browsers became widely available in the mid 1990s. "
            "The rise of social media changed how people communicate online. "
            "Mobile internet access has grown rapidly in recent years."
        )
        metrics = self.scorer.readability_metrics(text)
        assert 40 <= metrics.flesch_reading_ease < 60
        assert metrics.reading_level == "difficult"

    def test_very_difficult_reading_level(self) -> None:
        # Complex academic text should score FRE < 40
        text = (
            "The analysis of economic systems requires understanding of supply and demand dynamics. "
            "Market equilibrium is determined by the intersection of these two fundamental forces. "
            "Prices adjust to balance quantity supplied with quantity demanded. "
            "Changes in consumer preferences can shift demand curves significantly. "
            "Production costs influence supply curves and market outcomes. "
            "Government intervention through taxation and subsidies affects market efficiency."
        )
        metrics = self.scorer.readability_metrics(text)
        assert metrics.flesch_reading_ease < 40
        assert metrics.reading_level == "very_difficult"

    def test_short_text_handling(self) -> None:
        text = "Hello world."
        fk = self.scorer.flesch_kincaid(text)
        assert isinstance(fk, float)

    def test_long_technical_text(self) -> None:
        text = (
            "Microservices architecture decomposes monolithic applications into "
            "independently deployable services that communicate via lightweight "
            "protocols. Container orchestration platforms such as Kubernetes provide "
            "automated scaling, load balancing, and fault tolerance mechanisms. "
            "Service mesh implementations like Istio enable sophisticated traffic "
            "management, mutual TLS encryption, and observability across distributed "
            "service topologies. Event-driven architectures utilizing Apache Kafka "
            "facilitate asynchronous communication patterns with at-least-once "
            "delivery semantics and horizontal scalability across partitions."
        )
        metrics = self.scorer.readability_metrics(text)
        assert isinstance(metrics, ReadabilityMetrics)
        assert metrics.flesch_kincaid > 0
        assert metrics.coleman_liau > 0

    def test_multiple_sentences_scoring(self) -> None:
        text = (
            "First sentence here. Second sentence adds more words to the total. "
            "Third sentence continues with additional information. "
            "Fourth sentence brings the count higher. Fifth sentence completes it."
        )
        fk = self.scorer.flesch_kincaid(text)
        cl = self.scorer.coleman_liau(text)
        fre = self.scorer.flesch_reading_ease(text)
        assert isinstance(fk, float)
        assert isinstance(cl, float)
        assert isinstance(fre, float)
        assert fre > 0
