"""Pre-dev contract tests: Content-Forge P0-1 Brief entity, persistence & validation.

Contract source: analysis/forge-spec.md §3.1 (commit 9c8cd2b).
Target package: src/forge/{constants.py, brief_schemas.py, brief_store.py}.

Suite layout (three layers):
  1. Spec-contract guards  -- GREEN now. Pin the committed spec §3.1 so signature
     drift in the contract source of truth fails loudly.
  2. Interface tests       -- SKIP while src/forge is absent (this task forbids
     NotImplementedError stubs, so there is nothing to import yet). Pure contract
     pins (imports + exact signatures/defaults) that must pass immediately once
     the developer creates the modules -- zero behavioral assumptions.
  3. Behavioral tests      -- RED until implementation. Imports live inside each
     test so the failure is a clean per-test ModuleNotFoundError, not a
     collection error.

NOTE -- spec inconsistency (flagged to orchestrator in t_70e0ac09): the §3.1
expectation block asserts ``validate() -> {"valid": False, "channels_empty"}``
directly after ``update_brief(..., channels=["email"])``. A latest version whose
``channels == ["email"]`` can never produce ``channels_empty`` under the
deterministic rules ("empty channels -> error channels_empty"). This suite
encodes the deterministic rules: the empty-channels case is pinned by its own
dedicated test and the valid case after the update flow is pinned positively.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_SECTION = REPO_ROOT / "analysis" / "forge-spec.md"

# Capability probe: no stubs are permitted by this task, so the forge package
# does not exist yet. Interface tests skip until the developer creates it;
# behavioral tests fail with ModuleNotFoundError (the intended RED signal).
HAS_FORGE = False
try:
    from forge import brief_schemas, brief_store  # noqa: F401
    from forge.constants import FORGE_CHANNELS  # noqa: F401

    HAS_FORGE = True
except ImportError:
    pass

requires_forge = pytest.mark.skipif(
    not HAS_FORGE,
    reason="RED phase: src/forge package does not exist yet (no stubs permitted)",
)


def _payload(**overrides) -> dict:
    """Minimal valid BriefCreate payload (spec §3.1)."""
    base = {
        "title": "Launch",
        "audience": "CTOs",
        "objective": "Drive adoption",
        "offer": "Free pilot",
        "primary_cta": "Book a demo",
        "channels": ["blog", "linkedin"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Layer 1 -- spec-contract guards (GREEN now; pin the committed spec)
# ---------------------------------------------------------------------------


def test_spec_guard_p0_1_files_declared():
    text = SPEC_SECTION.read_text()
    for line in (
        "src/forge/constants.py",
        "src/forge/brief_schemas.py",
        "src/forge/brief_store.py",
    ):
        assert line in text, f"spec §3.1 must declare {line}"


def test_spec_guard_class_and_constant_signatures():
    text = SPEC_SECTION.read_text()
    for line in (
        "FORGE_CHANNELS: frozenset[str]",
        "class OutputConstraints(BaseModel):",
        "class BriefCreate(BaseModel):",
        "class Brief(BriefCreate):",
        "class BriefStore:",
    ):
        assert line in text, f"spec §3.1 must declare {line}"


def test_spec_guard_store_method_signatures():
    text = SPEC_SECTION.read_text()
    for line in (
        'def create_brief(self, payload: BriefCreate, created_by: str = "system") -> Brief',
        "def get_brief(self, brief_id: str) -> Brief",
        "def update_brief(self, brief_id: str, payload: BriefCreate, created_by: str) -> Brief",
        "def versions(self, brief_id: str) -> list[Brief]",
        "def validate(self, brief_id: str) -> dict",
        "def archive_brief(self, brief_id: str) -> None",
    ):
        assert line in text, f"spec §3.1 must declare {line}"


def test_spec_guard_validation_rule_codes():
    text = SPEC_SECTION.read_text()
    for code in (
        "channels_empty",
        "output_constraints_channel_mismatch",
        "duplicate_prohibited_phrase",
    ):
        assert code in text, f"spec §3.1 must declare error/warning code {code}"


# ---------------------------------------------------------------------------
# Layer 2 -- interface tests (imports + exact signatures; SKIP until forge exists)
# ---------------------------------------------------------------------------


@requires_forge
def test_interface_forge_channels_constant():
    from forge.constants import FORGE_CHANNELS

    assert isinstance(FORGE_CHANNELS, frozenset)
    assert FORGE_CHANNELS == frozenset(
        {"blog", "email", "linkedin", "x", "instagram", "landing", "script"}
    )


@requires_forge
def test_interface_output_constraints_fields_and_defaults():
    from forge.brief_schemas import OutputConstraints

    for field in (
        "length", "tone", "reading_level", "keywords", "required_sections", "hashtags",
    ):
        assert field in OutputConstraints.model_fields

    oc = OutputConstraints()
    assert oc.length == "medium"
    assert oc.tone == "professional"
    assert oc.reading_level == "general"
    assert oc.keywords == []
    assert oc.required_sections == []
    assert oc.hashtags is None

    overridden = OutputConstraints(length="long", hashtags=5, keywords=["kpi"])
    assert overridden.length == "long"
    assert overridden.hashtags == 5
    assert overridden.keywords == ["kpi"]

    with pytest.raises(ValidationError):
        OutputConstraints(hashtags="5")  # hashtags is int | None


@requires_forge
def test_interface_brief_create_fields_and_defaults():
    from forge.brief_schemas import BriefCreate

    for field in (
        "title", "audience", "objective", "offer", "primary_cta", "language",
        "brand_profile_id", "channels", "sources", "required_claims",
        "prohibited_phrases", "output_constraints",
    ):
        assert field in BriefCreate.model_fields

    bc = BriefCreate(title="t", audience="a", objective="o", offer="f", primary_cta="c")
    assert bc.language == "en"
    assert bc.brand_profile_id is None
    assert bc.channels == []
    assert bc.sources == []
    assert bc.required_claims == []
    assert bc.prohibited_phrases == []
    assert bc.output_constraints == {}


@requires_forge
def test_interface_brief_create_length_constraints():
    from forge.brief_schemas import BriefCreate

    with pytest.raises(ValidationError):
        BriefCreate()  # all five core fields required
    with pytest.raises(ValidationError):
        BriefCreate(title="", audience="a", objective="o", offer="f", primary_cta="c")
    with pytest.raises(ValidationError):
        BriefCreate(title="x" * 201, audience="a", objective="o", offer="f", primary_cta="c")
    with pytest.raises(ValidationError):
        BriefCreate(title="t", audience="a", objective="o", offer="f", primary_cta="c" * 501)
    with pytest.raises(ValidationError):
        BriefCreate(title="t", audience="a" * 2001, objective="o", offer="f", primary_cta="c")


@requires_forge
def test_interface_brief_fields_and_defaults():
    from forge.brief_schemas import Brief

    for field in ("brief_id", "version", "status", "created_by", "created_at"):
        assert field in Brief.model_fields

    b = Brief(**_payload(), brief_id="br-1", created_at=1.5)
    assert b.version == 1
    assert b.status == "draft"
    assert b.created_by == "system"
    assert b.brief_id == "br-1"
    assert b.created_at == 1.5

    with pytest.raises(ValidationError):
        Brief(**_payload(), created_at=1.0)  # brief_id required
    with pytest.raises(ValidationError):
        Brief(**_payload(), brief_id="x", created_at=1.0, status="published")  # Literal


@requires_forge
def test_interface_brief_store_method_signatures():
    from forge.brief_schemas import Brief
    from forge.brief_store import BriefStore

    sig = inspect.signature(BriefStore.__init__)
    assert list(sig.parameters) == ["self", "path"]

    sig = inspect.signature(BriefStore.create_brief)
    assert list(sig.parameters) == ["self", "payload", "created_by"]
    assert sig.parameters["created_by"].default == "system"
    ret = sig.return_annotation
    assert ret is Brief or ret == "Brief"

    sig = inspect.signature(BriefStore.get_brief)
    assert list(sig.parameters) == ["self", "brief_id"]
    ret = sig.return_annotation
    assert ret is Brief or ret == "Brief"

    sig = inspect.signature(BriefStore.update_brief)
    assert list(sig.parameters) == ["self", "brief_id", "payload", "created_by"]
    assert sig.parameters["created_by"].default is inspect.Parameter.empty
    ret = sig.return_annotation
    assert ret is Brief or ret == "Brief"

    sig = inspect.signature(BriefStore.versions)
    assert list(sig.parameters) == ["self", "brief_id"]
    ret = sig.return_annotation
    assert ret == "list[Brief]" or getattr(ret, "__origin__", None) is list

    sig = inspect.signature(BriefStore.validate)
    assert list(sig.parameters) == ["self", "brief_id"]
    ret = sig.return_annotation
    assert ret is dict or ret == "dict"

    sig = inspect.signature(BriefStore.archive_brief)
    assert list(sig.parameters) == ["self", "brief_id"]
    ret = sig.return_annotation
    assert ret is None or ret == "None"


# ---------------------------------------------------------------------------
# Layer 3 -- behavioral tests (RED until implementation)
# ---------------------------------------------------------------------------


def test_behavior_spec_expectation_flow(tmp_path):
    """Mirrors the §3.1 expectation block verbatim (create -> get -> update ->
    versions -> latest). The block's validate() line is inconsistent with the
    deterministic rules (see module docstring) and is pinned separately."""
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(
        BriefCreate(
            title="Launch", audience="CTOs", objective="...", offer="...",
            primary_cta="...", channels=["blog", "linkedin"],
        )
    )
    assert b.brief_id
    assert b.version == 1
    assert b.status == "draft"
    assert store.get_brief(b.brief_id).title == "Launch"

    b2 = store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    assert b2.version == 2
    assert b.version == 1  # old version immutable & retrievable
    assert len(store.versions(b.brief_id)) == 2
    assert store.get_brief(b.brief_id).channels == ["email"]  # get_brief returns LATEST

    with pytest.raises(KeyError):
        store.get_brief("nope")


def test_behavior_create_brief_records_creator(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()), created_by="alice")
    assert b.created_by == "alice"


def test_behavior_get_brief_missing_raises_keyerror(tmp_path):
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    with pytest.raises(KeyError):
        store.get_brief("nope")


def test_behavior_brief_ids_unique(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b1 = store.create_brief(BriefCreate(**_payload()))
    b2 = store.create_brief(BriefCreate(**_payload(title="Second")))
    assert b1.brief_id != b2.brief_id


def test_behavior_update_bumps_version_immutable_old(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    b2 = store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    assert b2.version == 2
    assert b.version == 1
    assert b2.created_by == "alice"
    assert b2.channels == ["email"]


def test_behavior_versions_oldest_to_newest(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    versions = store.versions(b.brief_id)
    assert len(versions) == 2
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].channels == ["blog", "linkedin"]
    assert versions[1].channels == ["email"]


def test_behavior_get_brief_returns_latest(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    assert store.get_brief(b.brief_id).version == 2
    assert store.get_brief(b.brief_id).channels == ["email"]


def test_behavior_multiple_updates_versioning(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    b3 = store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["x"])), created_by="bob"
    )
    assert b3.version == 3
    assert [v.version for v in store.versions(b.brief_id)] == [1, 2, 3]
    assert store.get_brief(b.brief_id).channels == ["x"]
    assert store.versions(b.brief_id)[0].channels == ["blog", "linkedin"]


def test_behavior_created_at_monotonic(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    b2 = store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    assert isinstance(b.created_at, float)
    assert isinstance(b2.created_at, float)
    assert b.created_at <= b2.created_at


def test_behavior_validate_contract_shape_and_valid_case(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    r = store.validate(b.brief_id)
    assert set(r) == {"valid", "errors", "warnings"}
    assert r["valid"] is True
    assert r["errors"] == []
    assert r["warnings"] == []


def test_behavior_validate_empty_channels_error(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload(channels=[])))
    r = store.validate(b.brief_id)
    assert r["valid"] is False
    assert "channels_empty" in r["errors"]


def test_behavior_validate_unknown_channel_error(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload(channels=["tiktok"])))
    r = store.validate(b.brief_id)
    assert r["valid"] is False
    assert r["errors"]  # channels must be subset of FORGE_CHANNELS


def test_behavior_validate_output_constraints_mismatch(tmp_path):
    from forge.brief_schemas import BriefCreate, OutputConstraints
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(
        BriefCreate(
            **_payload(
                channels=["blog"],
                output_constraints={"instagram": OutputConstraints()},
            )
        )
    )
    r = store.validate(b.brief_id)
    assert r["valid"] is False
    assert "output_constraints_channel_mismatch" in r["errors"]


def test_behavior_validate_output_constraints_matching_keys_ok(tmp_path):
    from forge.brief_schemas import BriefCreate, OutputConstraints
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(
        BriefCreate(
            **_payload(
                channels=["blog", "instagram"],
                output_constraints={
                    "blog": OutputConstraints(),
                    "instagram": OutputConstraints(),
                },
            )
        )
    )
    r = store.validate(b.brief_id)
    assert r["valid"] is True
    assert "output_constraints_channel_mismatch" not in r["errors"]


def test_behavior_validate_duplicate_prohibited_phrase_warning(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(
        BriefCreate(**_payload(channels=["blog"], prohibited_phrases=["cringe", "cringe"]))
    )
    r = store.validate(b.brief_id)
    assert r["valid"] is True  # warning only
    assert "duplicate_prohibited_phrase" in r["warnings"]
    assert r["errors"] == []


def test_behavior_validate_empty_entries_invalid(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(
        BriefCreate(
            **_payload(channels=["blog"], required_claims=[""], prohibited_phrases=[""])
        )
    )
    r = store.validate(b.brief_id)
    assert r["valid"] is False
    assert r["errors"]  # required_claims / prohibited_phrases entries must be non-empty


def test_behavior_persistence_across_reopen(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    path = tmp_path / "briefs.db"
    store = BriefStore(path)
    b = store.create_brief(BriefCreate(**_payload()))
    reopened = BriefStore(path)
    assert reopened.get_brief(b.brief_id).title == "Launch"
    assert len(reopened.versions(b.brief_id)) == 1


def test_behavior_store_accepts_str_and_path(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    path = tmp_path / "briefs.db"
    store = BriefStore(str(path))
    b = store.create_brief(BriefCreate(**_payload()))
    assert BriefStore(path).get_brief(b.brief_id).title == "Launch"


def test_behavior_archive_sets_status_archived(tmp_path):
    from forge.brief_schemas import BriefCreate
    from forge.brief_store import BriefStore

    store = BriefStore(tmp_path / "briefs.db")
    b = store.create_brief(BriefCreate(**_payload()))
    store.update_brief(
        b.brief_id, BriefCreate(**_payload(channels=["email"])), created_by="alice"
    )
    store.archive_brief(b.brief_id)
    assert store.get_brief(b.brief_id).status == "archived"
    assert store.get_brief(b.brief_id).version == 2
