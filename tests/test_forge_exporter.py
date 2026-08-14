"""Pre-development contract tests: Content-Forge P0-6 (analysis/forge-spec.md §3.6).

Byte-faithful export + disclosure metadata (MVP FR-24, FR-25, FR-27; US-005).

Target package: src/forge/exporter.py (spec §3.6; commit 9c8cd2b / fd0b99f).

Export is a PURE function over the frozen approved snapshot — it NEVER reads
live store state (research hint 10: byte-level fidelity, no silent alteration).

Suite layout (three layers, repo convention):
  1. Spec-contract guards  -- GREEN now. Pin the committed spec §3.6 so
     signature drift in the contract source of truth fails loudly.
  2. Interface tests       -- SKIP while src/forge is absent (no stubs
     permitted). Pure contract pins (imports + exact signatures/defaults) that
     must pass immediately once the developer creates the module.
  3. Behavioral tests      -- RED until implementation (assert-based; the
     store is untouched by export — proven by asserting content unchanged).

Expectations are behavioral (assert-based), NOT pytest.raises(NotImplementedError)
stub-guards.
"""

from __future__ import annotations

import hashlib
import inspect
from enum import Enum
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_SECTION = REPO_ROOT / "analysis" / "forge-spec.md"

# Capability probe: no stubs are permitted by this task, so the forge package
# does not exist yet. Interface tests skip until the developer creates it;
# behavioral tests fail with ModuleNotFoundError (the intended RED signal).
HAS_FORGE = False
try:
    from forge.exporter import (  # noqa: F401
        Exporter,
        ExportFormat,
        ExportRequest,
        ExportResult,
    )

    HAS_FORGE = True
except ImportError:
    pass

requires_forge = pytest.mark.skipif(
    not HAS_FORGE,
    reason="RED phase: src/forge package does not exist yet (no stubs permitted)",
)

BODY = "Announcing Acme 2.0 \u2014 now with AI workflows.\n\nLearn more at acme.com."
HASH = hashlib.sha256(BODY.encode()).hexdigest()


def _request(**overrides) -> ExportRequest:
    from forge.exporter import ExportFormat, ExportRequest

    base = {
        "draft_id": "d1",
        "approved_body": BODY,
        "approved_hash": HASH,
        "channel": "linkedin",
        "format": ExportFormat.txt,
    }
    base.update(overrides)
    return ExportRequest(**base)


# ---------------------------------------------------------------------------
# Layer 1 -- spec-contract guards (GREEN now; pin the committed spec)
# ---------------------------------------------------------------------------


def test_spec_guard_p0_6_files_declared():
    text = SPEC_SECTION.read_text()
    for line in ("src/forge/exporter.py", "src/forge/export_schemas.py"):
        assert line in text, f"spec §3.6 must declare {line}"


def test_spec_guard_export_classes_declared():
    text = SPEC_SECTION.read_text()
    for line in (
        "class ExportFormat(str, Enum):",
        "class ExportRequest(BaseModel):",
        "class ExportResult(BaseModel):",
        "class Exporter:",
    ):
        assert line in text, f"spec §3.6 must declare {line}"


def test_spec_guard_export_signatures():
    text = SPEC_SECTION.read_text()
    for line in (
        "def export(self, req: ExportRequest) -> ExportResult: ...",
        "def preflight(self, req: ExportRequest) -> dict:",
    ):
        assert line in text, f"spec §3.6 must declare {line}"


def test_spec_guard_export_invariants():
    text = SPEC_SECTION.read_text()
    for invariant in (
        "visible_fidelity",
        "approved_body",
        "approved_hash",
        "include_disclosure",
        "application/ld+json",
        "ai-generated",
    ):
        assert invariant in text, f"spec §3.6 must mention {invariant}"


# ---------------------------------------------------------------------------
# Layer 2 -- interface tests (imports + exact signatures; SKIP until forge exists)
# ---------------------------------------------------------------------------


@requires_forge
def test_interface_export_format_enum_members():
    from forge.exporter import ExportFormat

    assert ExportFormat.txt.value == "txt"
    assert ExportFormat.md.value == "md"
    assert ExportFormat.html.value == "html"
    assert ExportFormat.json.value == "json"
    assert issubclass(ExportFormat, str)
    assert issubclass(ExportFormat, Enum)


@requires_forge
def test_interface_export_request_fields_and_defaults():
    from forge.exporter import ExportRequest

    for field in (
        "draft_id",
        "approved_body",
        "approved_hash",
        "channel",
        "format",
        "include_provenance",
        "include_disclosure",
    ):
        assert field in ExportRequest.model_fields

    req = ExportRequest(
        draft_id="d1",
        approved_body=BODY,
        approved_hash=HASH,
        channel="linkedin",
        format=ExportFormat.txt,
    )
    assert req.include_provenance is False
    assert req.include_disclosure is True


@requires_forge
def test_interface_export_result_fields():
    from forge.exporter import ExportResult

    for field in ("artifact_id", "filename", "content", "content_hash", "visible_fidelity"):
        assert field in ExportResult.model_fields


@requires_forge
def test_interface_exporter_method_signatures():
    from forge.exporter import Exporter

    export_sig = inspect.signature(Exporter.export)
    assert list(export_sig.parameters) == ["self", "req"]

    preflight_sig = inspect.signature(Exporter.preflight)
    assert list(preflight_sig.parameters) == ["self", "req"]


@requires_forge
def test_interface_exporter_default_constructible():
    from forge.exporter import Exporter

    assert isinstance(Exporter(), Exporter)


# ---------------------------------------------------------------------------
# Layer 3 -- behavioral tests (RED until implementation)
# ---------------------------------------------------------------------------


def test_behavior_spec_expectation_flow():
    """Mirrors the §3.6 expectation block verbatim (txt golden, md fidelity,
    html disclosure, preflight hash mismatch, store untouched)."""
    from forge.exporter import Exporter, ExportFormat, ExportRequest

    ex = Exporter()
    h = hashlib.sha256(BODY.encode()).hexdigest()
    r = ex.export(
        ExportRequest(
            draft_id="d1",
            approved_body=BODY,
            approved_hash=h,
            channel="linkedin",
            format=ExportFormat.txt,
        )
    )
    assert r.visible_fidelity is True
    assert r.content.strip() == BODY
    assert r.filename == f"d1-linkedin-{h[:8]}.txt"

    r_md = ex.export(
        ExportRequest(
            draft_id="d1",
            approved_body=BODY,
            approved_hash=h,
            channel="linkedin",
            format=ExportFormat.md,
        )
    )
    assert r_md.visible_fidelity is True

    r_html = ex.export(
        ExportRequest(
            draft_id="d1",
            approved_body=BODY,
            approved_hash=h,
            channel="linkedin",
            format=ExportFormat.html,
            include_disclosure=True,
        )
    )
    assert "application/ld+json" in r_html.content
    assert "ai-generated" in r_html.content

    pf = ex.preflight(
        ExportRequest(
            draft_id="d1",
            approved_body=BODY,
            approved_hash="deadbeef",
            channel="x",
            format=ExportFormat.txt,
        )
    )
    assert pf["ok"] is False and any("hash" in e for e in pf["errors"])


def test_behavior_export_is_pure_store_untouched(tmp_path):
    """Export is a pure function over the frozen snapshot — the store/draft
    content is byte-identical before and after (spec §3.6 + research hint 10)."""
    from forge.exporter import Exporter, ExportFormat, ExportRequest

    from src.product_ops import ContentOpsStore

    store = ContentOpsStore(tmp_path / "ops.db")
    campaign = store.create_campaign("Launch", ["linkedin"], brief="...")
    asset = store.create_asset(campaign, "linkedin", BODY, "Launch post", author="alice")

    ex = Exporter()
    ex.export(
        ExportRequest(
            draft_id=asset,
            approved_body=BODY,
            approved_hash=HASH,
            channel="linkedin",
            format=ExportFormat.txt,
        )
    )
    ex.export(
        ExportRequest(
            draft_id=asset,
            approved_body=BODY,
            approved_hash=HASH,
            channel="linkedin",
            format=ExportFormat.html,
            include_disclosure=True,
        )
    )
    # store untouched — the frozen snapshot is all export ever sees
    assert store.asset(asset)["content"] == BODY


def test_behavior_txt_is_exact_body_modulo_trailing_newline():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r = ex.export(_request(format=ExportFormat.txt))
    assert r.visible_fidelity is True
    # byte-level: no silent alteration; trailing newline allowed
    assert r.content.strip() == BODY
    assert r.content_hash == hashlib.sha256(r.content.encode()).hexdigest()


def test_behavior_txt_filename_deterministic():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r1 = ex.export(_request(format=ExportFormat.txt))
    r2 = ex.export(_request(format=ExportFormat.txt))
    assert r1.filename == r2.filename
    assert r1.filename == f"d1-linkedin-{HASH[:8]}.txt"


def test_behavior_export_artifact_ids_unique_per_export():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    a = ex.export(_request(format=ExportFormat.txt))
    b = ex.export(_request(format=ExportFormat.md))
    assert a.artifact_id != b.artifact_id
    assert a.artifact_id and b.artifact_id


def test_behavior_md_wrapper_strips_to_exact_body():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r = ex.export(_request(format=ExportFormat.md))
    assert r.visible_fidelity is True
    # wrapper must not alter the approved body — byte-level fidelity
    assert BODY in r.content


def test_behavior_html_escapes_and_paragraphs():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r = ex.export(
        _request(format=ExportFormat.html, include_disclosure=False)
    )
    assert r.visible_fidelity is True
    assert "<p>" in r.content
    assert "Acme" in r.content
    # no disclosure script when include_disclosure=False
    assert "application/ld+json" not in r.content
    assert "ai-generated" not in r.content


def test_behavior_html_disclosure_jsonld_marker():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r = ex.export(
        _request(format=ExportFormat.html, include_disclosure=True)
    )
    assert r.visible_fidelity is True
    # EU AI Act Art. 50(2): machine-readable ai-generated marker
    assert "application/ld+json" in r.content
    assert "ai-generated" in r.content


def test_behavior_json_contains_exact_body():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    r = ex.export(_request(format=ExportFormat.json))
    assert r.visible_fidelity is True
    assert '"content"' in r.content
    assert BODY in r.content


def test_behavior_visible_fidelity_true_for_all_formats():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    for fmt in ExportFormat:
        r = ex.export(_request(format=fmt))
        assert r.visible_fidelity is True, f"{fmt} must be byte-faithful"


def test_behavior_preflight_ok_true_on_match():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    pf = ex.preflight(_request(format=ExportFormat.txt))
    assert pf["ok"] is True
    assert pf["errors"] == []


def test_behavior_preflight_hash_mismatch_error():
    from forge.exporter import Exporter, ExportFormat

    ex = Exporter()
    pf = ex.preflight(
        _request(approved_hash="deadbeef", format=ExportFormat.txt)
    )
    assert pf["ok"] is False
    assert any("hash" in e for e in pf["errors"])


def test_behavior_preflight_channel_char_limit_error():
    from forge.exporter import Exporter, ExportFormat, ExportRequest

    ex = Exporter()
    long_body = "y" * 500
    pf = ex.preflight(
        ExportRequest(
            draft_id="d1",
            approved_body=long_body,
            approved_hash=hashlib.sha256(long_body.encode()).hexdigest(),
            channel="x",
            format=ExportFormat.txt,
        )
    )
    assert pf["ok"] is False
    assert any("char" in e or "limit" in e for e in pf["errors"])
