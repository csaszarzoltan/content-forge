"""Interface and behavioral pre-dev tests for the content-creation pipeline.

Covers acceptance criteria US-001..US-004 from analysis-brief.md
(analysis/analysis-brief.md, t_ef548473) — the "turn one source asset into a
consistent cross-platform content package" workflow:

  US-001  Create a cross-platform content package (source → variants → publish)
  US-002  Validate and correct inputs before running
  US-003  Recover safely from interrupted/external-dependency failures
  US-004  Review history, status, and outcomes (audit trail)

Test policy (pre-dev contract, repo convention — see test_video_jobs.py):
  * INTERFACE tests — importability, class/field/signature/route existence.
    They PASS immediately once the stubbed modules exist.
  * BEHAVIORAL tests — expected runtime behavior of the implemented
    pipeline. They FAIL during RED phase (modules missing/raise) and MUST
    PASS after the developer implements per the brief.
  * NO inverse stub-guards: no test asserts NotImplementedError as the
    expected behavior of the feature's own public methods.

Canonical API (brief §6):
  POST /api/v1/content-packages        (Idempotency-Key header required)
  GET  /api/v1/content-packages/{id}
  POST /api/v1/content-packages/{id}/generate
  POST /api/v1/content-packages/{id}/validate
  POST /api/v1/content-packages/{id}/approve
  POST /api/v1/content-packages/{id}/publish  (Idempotency-Key required)
  GET  /api/v1/content-packages/{id}/history

Run with the repo venv only:
    PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_content_creation.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

# ── Store ───────────────────────────────────────────────────────────────────
from src.product_ops import ContentPackageStore

# ── Router ─────────────────────────────────────────────────────────────────
from src.routers.content_packages import router as content_packages_router

# ── Schemas ────────────────────────────────────────────────────────────────
from src.schemas.content_packages import (
    ContentPackageCreate,
    ContentPackageHistory,
    ContentPackageResponse,
    ContentVariantResponse,
)

# ── Services ────────────────────────────────────────────────────────────────
from src.services.platform_adapter import PLATFORM_PROMPTS, PlatformAdapter, PlatformVariant

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS once the modules exist)
# ============================================================================

# ── Package state machine ───────────────────────────────────────────────────


class TestContentPackageStoreInterface:
    """US-001 — ContentPackageStore class + mandated methods exist."""

    def test_store_class_exists(self):
        assert callable(ContentPackageStore)

    def test_store_constructor_takes_path(self):
        import inspect

        sig = inspect.signature(ContentPackageStore.__init__)
        params = list(sig.parameters)
        assert "path" in params, f"constructor must accept a path; got {params}"

    def test_store_has_mandated_methods(self):
        for method in (
            "create_package",
            "get_package",
            "update_state",
            "save_variants",
            "get_variants",
            "update_variant",
            "approve",
            "audit",
            "history",
        ):
            assert callable(getattr(ContentPackageStore, method, None)), (
                f"ContentPackageStore.{method} missing"
            )

    def test_create_package_returns_stable_id(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello world", platforms=["linkedin"]
        )
        assert isinstance(pkg.get("id"), str) and pkg["id"]
        assert pkg["state"] == "draft"

    def test_get_package_round_trips(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello", platforms=["twitter", "email"]
        )
        record = store.get_package(pkg["id"])
        assert record["id"] == pkg["id"]
        assert record["source_type"] == "text"
        assert set(record["platforms"]) == {"twitter", "email"}

    def test_state_chain_order(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello", platforms=["linkedin"]
        )
        for state in ("generating", "validating", "ready_to_approve", "approved", "publishing", "published"):
            store.update_state(pkg["id"], state)
            assert store.get_package(pkg["id"])["state"] == state

    def test_any_state_can_fail(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello", platforms=["linkedin"]
        )
        store.update_state(pkg["id"], "generating")
        store.update_state(pkg["id"], "failed")
        assert store.get_package(pkg["id"])["state"] == "failed"

    def test_variant_methods(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello", platforms=["twitter"]
        )
        store.save_variants(
            pkg["id"], [{"platform": "twitter", "content": "Hi", "char_count": 2}]
        )
        variants = store.get_variants(pkg["id"])
        assert len(variants) == 1
        assert variants[0]["platform"] == "twitter"
        assert "validation_status" in variants[0]
        assert "publish_status" in variants[0]

    def test_audit_and_history(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hello", platforms=["linkedin"]
        )
        store.audit(pkg["id"], "CREATED", {"source": "text"})
        events = store.history(pkg["id"])
        assert any(e["kind"] == "CREATED" for e in events)


# ── Schemas ─────────────────────────────────────────────────────────────────


class TestContentPackageSchemasInterface:
    """Pydantic v2 schemas exist with the mandated fields."""

    def test_create_schema_fields(self):
        fields = set(ContentPackageCreate.model_fields)
        assert {"source_type", "source_ref", "platforms"} <= fields

    def test_create_schema_source_types(self):
        from src.schemas.content_packages import ContentSourceType

        values = {s.value for s in ContentSourceType}
        assert {"generation_id", "text", "url"} == values

    def test_response_schema_fields(self):
        fields = set(ContentPackageResponse.model_fields)
        assert {
            "id",
            "source_type",
            "source_ref",
            "state",
            "platforms",
            "variants",
        } <= fields

    def test_variant_schema_fields(self):
        fields = set(ContentVariantResponse.model_fields)
        assert {
            "id",
            "platform",
            "content",
            "validation_status",
            "publish_status",
        } <= fields

    def test_history_schema_fields(self):
        fields = set(ContentPackageHistory.model_fields)
        assert "events" in fields


# ── PlatformAdapter ─────────────────────────────────────────────────────────


class TestPlatformAdapterInterface:
    """P0-3 — PlatformAdapter exists with adapt() and per-platform prompts."""

    def test_adapter_class_exists(self):
        assert callable(PlatformAdapter)

    def test_adapt_is_async(self):
        import inspect

        assert inspect.iscoroutinefunction(PlatformAdapter.adapt)

    def test_platform_prompts_cover_platforms(self):
        for platform in ("linkedin", "twitter", "email", "blog"):
            assert platform in PLATFORM_PROMPTS, f"missing prompt for {platform}"

    def test_platform_variant_fields(self):
        fields = set(PlatformVariant.model_fields)
        assert {
            "platform",
            "content",
            "char_count",
            "adapted_from",
            "model_used",
        } <= fields


# ── Router ──────────────────────────────────────────────────────────────────


class TestContentPackagesRouterInterface:
    """P0-2 — router registered with the canonical prefix + endpoints."""

    def test_router_prefix(self):
        assert content_packages_router.prefix == "/api/v1/content-packages"

    def test_router_has_endpoints(self):
        paths = {route.path for route in content_packages_router.routes}
        expected = {
            "/api/v1/content-packages",
            "/api/v1/content-packages/{package_id}",
            "/api/v1/content-packages/{package_id}/generate",
            "/api/v1/content-packages/{package_id}/validate",
            "/api/v1/content-packages/{package_id}/approve",
            "/api/v1/content-packages/{package_id}/publish",
            "/api/v1/content-packages/{package_id}/history",
        }
        assert expected <= paths, f"missing routes; have {paths}"


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (should PASS after implementation)
# ============================================================================

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path: Path) -> ContentPackageStore:
    """Fresh store on a temp SQLite DB per test."""
    return ContentPackageStore(tmp_path / "content-packages.db")


@pytest.fixture
def client(tmp_path: Path):
    """Standalone FastAPI app with only the content-packages router."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.include_router(content_packages_router)
    import src.routers.content_packages as cp_module

    cp_module._DB = tmp_path / "content-packages-api.db"
    return TestClient(app)


def _valid_body(**overrides) -> dict:
    body = {
        "source_type": "text",
        "source_ref": "A short source asset for adaptation.",
        "platforms": ["twitter", "linkedin"],
        "brand_voice_id": None,
    }
    body.update(overrides)
    return body


# ── P0-1 — ContentPackageStore + state machine ──────────────────────────────


class TestContentPackageStoreBehavior:
    """US-001/P0-1 — create/get/state transitions/variants/audit/idempotency."""

    def test_create_package_creates_variant_rows(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter", "linkedin", "email"]
        )
        variants = store.get_variants(pkg["id"])
        assert len(variants) == 3
        assert {v["platform"] for v in variants} == {"twitter", "linkedin", "email"}
        assert all(v["validation_status"] == "pending" for v in variants)

    def test_invalid_transition_rejected(self, store: ContentPackageStore):
        """ready_to_approve → generating must be rejected (no backwards jumps)."""
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["linkedin"]
        )
        store.update_state(pkg["id"], "generating")
        store.update_state(pkg["id"], "validating")
        store.update_state(pkg["id"], "ready_to_approve")
        with pytest.raises(ValueError, match="invalid_transition"):
            store.update_state(pkg["id"], "generating")

    def test_restart_safe(self, tmp_path: Path):
        """A new store instance on the same DB sees the package and its state."""
        db = tmp_path / "cp-restart.db"
        first = ContentPackageStore(db)
        pkg = first.create_package(
            source_type="text", source_ref="Hi", platforms=["linkedin"]
        )
        first.update_state(pkg["id"], "generating")
        first.update_state(pkg["id"], "validating")
        second = ContentPackageStore(db)
        record = second.get_package(pkg["id"])
        assert record["state"] == "validating"

    def test_save_and_update_variant(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter"]
        )
        store.save_variants(
            pkg["id"], [{"platform": "twitter", "content": "Adapted!", "char_count": 8}]
        )
        variant = store.get_variants(pkg["id"])[0]
        assert variant["content"] == "Adapted!"
        store.update_variant(pkg["id"], variant["id"], validation_status="validated")
        assert store.get_variants(pkg["id"])[0]["validation_status"] == "validated"

    def test_approve_requires_all_validated(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter", "linkedin"]
        )
        store.save_variants(
            pkg["id"],
            [
                {"platform": "twitter", "content": "T", "char_count": 1},
                {"platform": "linkedin", "content": "L", "char_count": 1},
            ],
        )
        store.update_state(pkg["id"], "generating")
        store.update_state(pkg["id"], "validating")
        store.update_state(pkg["id"], "ready_to_approve")
        with pytest.raises(ValueError, match="not_all_validated"):
            store.approve(pkg["id"])
        for variant in store.get_variants(pkg["id"]):
            store.update_variant(pkg["id"], variant["id"], validation_status="validated")
        result = store.approve(pkg["id"])
        assert result["state"] == "approved"

    def test_audit_events_appended(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter"]
        )
        store.update_state(pkg["id"], "generating")
        store.update_state(pkg["id"], "validating")
        events = store.history(pkg["id"])
        kinds = [e["kind"] for e in events]
        assert any("CREAT" in k for k in kinds)
        assert "generating" in " ".join(str(e.get("payload")) for e in events)


# ── P0-2 — API behavior (TestClient against the content-packages router) ────


class TestContentPackagesApiBehavior:
    """US-001/US-002 — create/get/generate/validate/approve/publish/history."""

    def test_create_returns_201_with_id(self, client):
        resp = client.post(
            "/api/v1/content-packages",
            json=_valid_body(),
            headers={"Idempotency-Key": "key-1"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["state"] == "draft"
        assert "id" in body

    def test_create_requires_idempotency_key(self, client):
        resp = client.post("/api/v1/content-packages", json=_valid_body())
        assert resp.status_code == 400, resp.text

    def test_create_rejects_empty_platforms(self, client):
        resp = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=[]),
            headers={"Idempotency-Key": "key-empty"},
        )
        assert resp.status_code == 400, resp.text

    def test_create_rejects_unknown_source_type(self, client):
        resp = client.post(
            "/api/v1/content-packages",
            json=_valid_body(source_type="podcast"),
            headers={"Idempotency-Key": "key-bad"},
        )
        assert resp.status_code == 422, resp.text

    def test_create_rejects_oversize_text(self, client):
        resp = client.post(
            "/api/v1/content-packages",
            json=_valid_body(source_ref="x" * 210_000),
            headers={"Idempotency-Key": "key-big"},
        )
        assert resp.status_code == 422, resp.text

    def test_create_idempotent_same_key_same_payload(self, client):
        first = client.post(
            "/api/v1/content-packages",
            json=_valid_body(),
            headers={"Idempotency-Key": "same-key"},
        )
        second = client.post(
            "/api/v1/content-packages",
            json=_valid_body(),
            headers={"Idempotency-Key": "same-key"},
        )
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] == second.json()["id"]

    def test_create_idempotency_collision_409(self, client):
        first = client.post(
            "/api/v1/content-packages",
            json=_valid_body(),
            headers={"Idempotency-Key": "collide"},
        )
        assert first.status_code == 201
        second = client.post(
            "/api/v1/content-packages",
            json=_valid_body(source_ref="different payload"),
            headers={"Idempotency-Key": "collide"},
        )
        assert second.status_code == 409, second.text

    def test_get_package_returns_variants(self, client):
        created = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=["twitter"]),
            headers={"Idempotency-Key": "get-1"},
        ).json()
        resp = client.get(f"/api/v1/content-packages/{created['id']}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["state"] == "draft"
        assert isinstance(body["variants"], list)
        assert "created_at" in body

    def test_get_unknown_package_404(self, client):
        resp = client.get("/api/v1/content-packages/nope")
        assert resp.status_code == 404, resp.text

    def test_generate_wrong_state_409(self, cp_client):
        cp_client.llm.script = {"twitter": ["post"], "linkedin": ["post"]}
        created = _create_package(cp_client, ["twitter", "linkedin"], key="gen-1")
        resp = cp_client.post(f"/api/v1/content-packages/{created['id']}/generate")
        assert resp.status_code == 200, resp.text
        assert resp.json()["state"] == "validating", resp.text
        # advance past generating → a generate from a non-retryable state must 409
        validated = cp_client.post(f"/api/v1/content-packages/{created['id']}/validate")
        assert validated.status_code == 200, validated.text
        assert validated.json()["state"] == "ready_to_approve", validated.text
        again = cp_client.post(f"/api/v1/content-packages/{created['id']}/generate")
        assert again.status_code == 409, again.text

    def test_validate_requires_generated_variants(self, client):
        created = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=["twitter"]),
            headers={"Idempotency-Key": "val-1"},
        ).json()
        resp = client.post(f"/api/v1/content-packages/{created['id']}/validate")
        assert resp.status_code in (200, 409), resp.text

    def test_approve_requires_validated_variants(self, client):
        created = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=["twitter"]),
            headers={"Idempotency-Key": "appr-1"},
        ).json()
        resp = client.post(f"/api/v1/content-packages/{created['id']}/approve")
        assert resp.status_code == 409, resp.text

    def test_publish_requires_idempotency_key(self, client):
        created = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=["twitter"]),
            headers={"Idempotency-Key": "pub-1"},
        ).json()
        resp = client.post(f"/api/v1/content-packages/{created['id']}/publish")
        assert resp.status_code == 400, resp.text

    def test_history_returns_audit_events(self, client):
        created = client.post(
            "/api/v1/content-packages",
            json=_valid_body(platforms=["twitter"]),
            headers={"Idempotency-Key": "hist-1"},
        ).json()
        resp = client.get(f"/api/v1/content-packages/{created['id']}/history")
        assert resp.status_code == 200, resp.text
        assert "events" in resp.json()

    def test_error_bodies_are_json(self, client):
        resp = client.get("/api/v1/content-packages/nope")
        assert resp.headers["content-type"].startswith("application/json")
        assert "detail" in resp.json()


# ── P0-7 — failure-recovery regression (US-003, tech-lead review t_1ba2653f) ──
#
# These tests pin the failure-recovery contract: a package whose generation
# partially failed must be retryable (regenerate ONLY the failed variants,
# preserving completed work) and validate-on-failed must never 500.


class _ScriptedLLM:
    """LLM stand-in whose behavior is driven by a per-platform call script.

    ``script`` maps platform → list of outcomes; each ``generate`` call pops
    the next outcome for that platform. An outcome is either an exception
    (raised, simulating an LLM outage) or a string (returned as the variant
    content). Exhausted platforms raise AssertionError so a test fails loudly
    if the handler calls the LLM more times than scripted.
    """

    def __init__(self, script: dict[str, list]):
        self.script = {p: list(seq) for p, seq in script.items()}
        self.calls: list[str] = []

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs):
        from src.services.llm_provider import LLMResponse

        platform = prompt.split(" for ")[1].split(".\n")[0]
        self.calls.append(platform)
        seq = self.script.get(platform)
        if not seq:
            raise AssertionError(f"unexpected generate call for {platform}")
        outcome = seq.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return LLMResponse(
            text=outcome,
            model_used="fake-model",
            tokens_prompt=10,
            tokens_completion=5,
            latency_ms=1,
        )


@pytest.fixture
def cp_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Content-packages TestClient with a scripted LLM injected.

    Monkeypatches the router module's ``_DB`` (fresh temp DB per test) and
    ``_adapter`` so generation never touches a real provider.
    """
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    import src.routers.content_packages as cp_module

    app = FastAPI()
    app.include_router(cp_module.router)
    cp_module._DB = tmp_path / "content-packages-api.db"

    llm = _ScriptedLLM({})

    def _fake_adapter():
        return PlatformAdapter(llm_provider=llm, registry=None)

    monkeypatch.setattr(cp_module, "_adapter", _fake_adapter)
    monkeypatch.setattr(cp_module, "_DB", cp_module._DB)

    client = TestClient(app)
    client.llm = llm  # type: ignore[attr-defined]
    return client


def _create_package(client, platforms: list[str], key: str = "recover-key") -> dict:
    resp = client.post(
        "/api/v1/content-packages",
        json=_valid_body(platforms=platforms),
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _cp_store() -> ContentPackageStore:
    """Store bound to the same DB the ``cp_client`` fixture uses."""
    import src.routers.content_packages as cp_module

    return ContentPackageStore(cp_module._DB)


class TestFailureRecovery:
    """US-003 — safe retry from ``failed`` (tech-lead review t_1ba2653f B1/B2)."""

    def test_validate_on_failed_package_returns_json_409_not_500(self, cp_client):
        """BLOCKER-2 — LLM outage → generate (failed) → validate must be a
        structured JSON 4xx (wrong_state), never an unhandled ValueError 500."""
        cp_client.llm.script = {"twitter": [RuntimeError("llm_unavailable")]}
        pkg = _create_package(cp_client, ["twitter"], key="b2-key")

        gen = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/generate")
        assert gen.status_code == 200, gen.text
        assert gen.json()["state"] == "failed", gen.text

        resp = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/validate")
        assert resp.status_code == 409, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        assert body["detail"] == "wrong_state"

    def test_regenerate_only_failed_variants(self, cp_client):
        """BLOCKER-1 — LLM outage → generate (partial failed) → retry must
        regenerate ONLY the failed variants; generated ones stay untouched."""
        cp_client.llm.script = {
            "twitter": [RuntimeError("llm_unavailable"), "retried twitter post"],
            "linkedin": ["original linkedin post"],
            "email": ["original email post"],
        }
        pkg = _create_package(cp_client, ["twitter", "linkedin", "email"], key="b1-key")

        gen = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/generate")
        assert gen.status_code == 200, gen.text
        body = gen.json()
        assert body["state"] == "failed", gen.text
        assert {e["platform"] for e in body["errors"]} == {"twitter"}

        # First pass must have called the LLM once per platform.
        assert sorted(cp_client.llm.calls) == ["email", "linkedin", "twitter"]

        # Simulate per-variant content generated during the first pass.
        store = _cp_store()
        for platform in ("linkedin", "email"):
            variant = next(
                v for v in store.get_variants(pkg["id"]) if v["platform"] == platform
            )
            store.update_variant(
                pkg["id"], variant["id"], content=f"original {platform} post"
            )

        cp_client.llm.calls.clear()
        retry = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/generate")
        assert retry.status_code == 200, retry.text
        assert retry.json()["state"] == "validating", retry.text

        # Retry must have touched ONLY the failed platform.
        assert cp_client.llm.calls == ["twitter"]
        store = _cp_store()
        variants = {v["platform"]: v for v in store.get_variants(pkg["id"])}
        assert variants["twitter"]["content"] == "retried twitter post"
        assert variants["linkedin"]["content"] == "original linkedin post"
        assert variants["email"]["content"] == "original email post"

    def test_failed_to_published_full_retry_flow(self, cp_client):
        """(c) failed → regenerate → validate → approve → publish reaches published."""
        cp_client.llm.script = {
            "twitter": [RuntimeError("llm_unavailable"), "retried twitter post"],
            "linkedin": ["linkedin post"],
        }
        pkg = _create_package(cp_client, ["twitter", "linkedin"], key="c-key")

        gen = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/generate")
        assert gen.status_code == 200, gen.text
        assert gen.json()["state"] == "failed", gen.text

        retry = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/generate")
        assert retry.status_code == 200, retry.text
        assert retry.json()["state"] == "validating", retry.text

        validated = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/validate")
        assert validated.status_code == 200, validated.text
        assert validated.json()["state"] == "ready_to_approve", validated.text

        approved = cp_client.post(f"/api/v1/content-packages/{pkg['id']}/approve")
        assert approved.status_code == 200, approved.text
        assert approved.json()["state"] == "approved", approved.text

        published = cp_client.post(
            f"/api/v1/content-packages/{pkg['id']}/publish",
            headers={"Idempotency-Key": "c-publish-key"},
        )
        assert published.status_code == 200, published.text
        assert published.json()["state"] == "published", published.text

    def test_failed_state_allows_retry_transitions(self, store: ContentPackageStore):
        """Store-level contract: failed → {generating, validating} are legal."""
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter"]
        )
        store.update_state(pkg["id"], "generating")
        store.update_state(pkg["id"], "failed")
        store.update_state(pkg["id"], "generating")
        assert store.get_package(pkg["id"])["state"] == "generating"
        store.update_state(pkg["id"], "validating")
        assert store.get_package(pkg["id"])["state"] == "validating"


# ── P0-3 — PlatformAdapter behavior ─────────────────────────────────────────


class TestPlatformAdapterBehavior:
    """US-001/P0-3 — LLM-based per-platform adaptation."""

    @pytest.mark.asyncio
    async def test_adapt_returns_variant(self):
        adapter = PlatformAdapter(llm_provider=_FakeLLM(), registry=None)
        variant = await adapter.adapt("Source text here.", "twitter", None)
        assert isinstance(variant, PlatformVariant)
        assert variant.platform == "twitter"
        assert variant.content
        assert variant.char_count > 0
        assert variant.adapted_from == "Source text here."

    @pytest.mark.asyncio
    async def test_adapt_idempotent_same_source(self):
        adapter = PlatformAdapter(llm_provider=_FakeLLM(), registry=None)
        first = await adapter.adapt("Same source.", "linkedin", None)
        second = await adapter.adapt("Same source.", "linkedin", None)
        assert first.content == second.content, "same source+platform must not re-generate"

    @pytest.mark.asyncio
    async def test_adapt_different_platforms_differ(self):
        adapter = PlatformAdapter(llm_provider=_FakeLLM(), registry=None)
        twitter = await adapter.adapt("Source.", "twitter", None)
        linkedin = await adapter.adapt("Source.", "linkedin", None)
        assert twitter.platform != linkedin.platform


class _FakeLLM:
    """Deterministic LLM stand-in for adapter tests."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs):
        from src.services.llm_provider import LLMResponse

        return LLMResponse(
            text="Adapted: " + prompt[:50],
            model_used="fake-model",
            tokens_prompt=10,
            tokens_completion=5,
            latency_ms=1,
        )


# ── P0-4/P0-5 — validation + publish wiring ─────────────────────────────────


class TestValidationPublishWiring:
    """US-002/US-003 — variant validation + publish update paths."""

    def test_validate_sets_validated_status(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter"]
        )
        store.save_variants(
            pkg["id"], [{"platform": "twitter", "content": "short", "char_count": 5}]
        )
        variant = store.get_variants(pkg["id"])[0]
        store.update_variant(pkg["id"], variant["id"], validation_status="validated")
        assert store.get_variants(pkg["id"])[0]["validation_status"] == "validated"

    def test_publish_records_remote_id(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["linkedin"]
        )
        store.save_variants(
            pkg["id"], [{"platform": "linkedin", "content": "post", "char_count": 4}]
        )
        variant = store.get_variants(pkg["id"])[0]
        store.update_variant(
            pkg["id"], variant["id"], publish_status="published", remote_id="urn:li:123"
        )
        assert store.get_variants(pkg["id"])[0]["publish_status"] == "published"
        assert store.get_variants(pkg["id"])[0]["remote_id"] == "urn:li:123"

    def test_publish_failure_records_error(self, store: ContentPackageStore):
        pkg = store.create_package(
            source_type="text", source_ref="Hi", platforms=["twitter"]
        )
        store.save_variants(
            pkg["id"], [{"platform": "twitter", "content": "x", "char_count": 1}]
        )
        variant = store.get_variants(pkg["id"])[0]
        store.update_variant(
            pkg["id"], variant["id"], publish_status="failed", error="publish_timeout"
        )
        assert store.get_variants(pkg["id"])[0]["publish_status"] == "failed"
        assert store.get_variants(pkg["id"])[0]["error"] == "publish_timeout"
