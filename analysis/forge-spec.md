# Content-Forge — Technical Specification (P0/P1/P2)

**Date:** 2026-08-14
**Analyst:** @analyst
**Task:** t_bf3f4a8d (child of roadmap root t_828d709c)
**Inputs:** `analysis/research-brief.md` (t_e60cffb1, commit 5081920), `analysis/product-scope.md` (t_f8320b99, commit 5642ed9), first-hand inspection of `/home/zoltan/contentforge` HEAD `8587575` (v0.16.0)
**Repo decision:** Implementation lands in the **dedicated contentforge repo `/home/zoltan/contentforge`** (origin `csaszarzoltan/contentforge`). The micro-saas-lab monorepo holds only coordination artifacts in `analysis/` (this file). Module path: `src/` flat layout (NOT `apps/`) — the repo has no `apps/` directory; the existing content-creation pipeline lives in `src/routers/content_packages.py` + `src/product_ops.py` + `src/schemas/content_packages.py`. New Content-Forge workspace modules go to `src/forge/` (new package), reusing `src/brand_voice/`, `src/constraints/`, `src/product_ops.py`, `src/services/`.

**Downstream consumers:** pre-tester (writes RED tests first), developer (implements to green), tester (verifies). This brief is the single source of truth for names, signatures, and acceptance commands.

---

## 1. Current State Assessment (verified at HEAD 8587575, 2026-08-14)

### 1.1 What already exists (reuse — do NOT rebuild)

| Capability | Location (contentforge) | Reuse decision |
|---|---|---|
| Brand voice profiles (VoiceProfile: identity, attributes, vocabulary preferred/banned, scenarios, formatting) | `src/brand_voice/models.py` (`VoiceProfile`, `VocabularyRules`) | P0 Brief links `brand_profile_id`; generation injects `to_system_prompt()` |
| Compliance scoring + banned-term detection | `src/brand_voice/compliance.py` (`ComplianceScorer`, `ComplianceResult`, `check_banned_terms`) | P0 blocked-term enforcement reuses `ComplianceScorer` as the deterministic engine |
| Platform constraint registry (max_chars, truncation_cutoff, max_hashtags, max_mentions, per-platform) | `src/constraints/models.py` (`TextConstraints`, `PlatformConstraints`), `src/constraints/registry.py` (`ConstraintRegistry`), `src/constraints/data/registry.json` | P0 channel-rule engine extends the registry with rule-type + severity; no new DB |
| Per-platform adaptation prompts (linkedin, twitter, email, …) | `src/services/platform_adapter.py` (`PlatformAdapter`, `PLATFORM_PROMPTS`, `PLATFORM_CONSTRAINTS_MAP`) | P0 drafting engine delegates per-channel adaptation here; extend `PLATFORM_PROMPTS` to all 7 channels |
| LLM provider abstraction | `src/services/llm_provider.py` (`get_provider`, `.generate(prompt, system_prompt, model)`) | P0 engine calls this only |
| Content generation orchestration | `src/services/generator.py` (`ContentGenerator.generate`, `GenerationResult`) | Extend `valid_types` to the 7 forge channels (currently `{blog, social, email}`) |
| Revision-bound approval workflow + audit trail (draft → in_review → approved/changes_requested, revision locking, stale-decision rejection, edit-after-approval invalidation) | `src/product_ops.py` `ContentOpsStore` (1743 lines, sync sqlite3): `create_campaign`, `create_asset`, `save_revision`, `request_asset_approval`, `decide_asset_approval`, `audit_events` | P0 review/approval reuses the state machine **unchanged**; adds claim-level gates + diff on top |
| Content package pipeline (source → variants → generate → validate → approve → publish, idempotency) | `src/routers/content_packages.py`, `src/schemas/content_packages.py`, `src/product_ops.py` `ContentPackageStore` | P0 forge draft lifecycle reuses `ContentPackageStore` where applicable; export is new |
| JSON-LD structured data generation | `src/services/jsonld_generator.py` | P0 export reuses for HTML/JSON provenance block |
| Testing conventions | `tests/` flat, pytest 9.1.1, `pythonpath=["src"]`, `addopts = "-n auto -q"`, ruff 0.16.1 (line-length 100, py311), .venv required | All acceptance commands below use the guard-biztos form |

### 1.2 Gaps vs. product scope (what P0 must build)

1. **Brief entity** — no structured, versioned Brief entity exists. `create_campaign(name, channels, brief: str)` takes a free-text brief string only. Product scope FR-01 needs a validated, immutable-by-version Brief with audience/objective/offer/CTA/language/sources/required_claims/prohibited_phrases/output_constraints.
2. **Multi-channel coordinated generation** — `PlatformAdapter.adapt()` covers linkedin/twitter/email (+ others in PLATFORM_PROMPTS) but the 7 forge channels (blog, email, linkedin, x, instagram, landing, script) are not a validated set, and there is no per-channel *rule* enforcement beyond char limits (FR-03: hard limits → non-compliant markers naming violated rules).
3. **Claim verification & provenance** — no verified-vs-suggestion classification, no mechanical citation span-overlap check, no stale-source warnings (FR-18..FR-20, FR-22). `ComplianceScorer` scores brand voice but never classifies factual claims.
4. **Blocked-term enforcement as a gate** — `ComplianceScorer.check_banned_terms` returns a list; nothing blocks approval/export on hits (FR-09 hard compliance gating needs an explicit exception mechanism).
5. **Export** — no export module at all (FR-24, FR-25, FR-27). `capture_provenance`/`export_provenance` exist in `ContentOpsStore` but only record model/prompt/voice version, never render approved snapshots byte-faithfully.
6. **Version diff** — `save_revision`/`revisions()`/`restore_revision` store full snapshots + optimistic concurrency, but there is no diff rendering between versions (FR-14).

### 1.3 Conventions to follow

- Python ≥3.11, pydantic v2 (BaseModel/Field), FastAPI routers under `src/routers/`, schemas under `src/schemas/`.
- `ContentOpsStore`/`ContentPackageStore` pattern: sync `sqlite3` with `_db()` context manager + JSON-encoded columns + `_id()` uuid hex + `_audit()` append-only events. Follow it for the new `BriefStore`.
- Tests: `tests/test_*.py`, pytest fixtures via `tests/conftest.py`, no modifications to existing test files.
- Commit convention: `feat(content-forge): …` / `fix(content-forge): …` (scope = module).
- All acceptance commands use the guard-biztos venv form; do NOT run bare pytest.

---

## 2. Clustered Options (considered & rejected/selected)

### Option A — Extend in place (SELECTED)
Add the workspace as `src/forge/` modules over the existing `ContentOpsStore`/`ContentPackageStore`/`ComplianceScorer`/`ConstraintRegistry` stack; extend `PlatformAdapter` prompts and `ConstraintRegistry` data rather than forking.
**Why:** the research brief's key finding — v0.16.0 already ships brand-voice compliance, banned-term detection, and platform constraints. The 1743-line `ContentOpsStore` already implements revision-locked approval with audit trail; rebuilding it duplicates ~500 lines of tested workflow state machine. Fastest path to a green MVP, lowest regression risk.

### Option B — New standalone service under monorepo `apps/content-forge` (REJECTED)
**Why:** the monorepo `micro-saas-lab` has no `apps/` layout (its `src/` is shared library code); the feature's home repo already exists with 1200+ tests and its own deployment (`railway.json`, Dockerfile). A new service would duplicate the entire brand-voice/constraints/provider stack. The monorepo keeps only `analysis/` docs.

### Option C — Guardrails-AI / NeMo Guardrails wrapper (REJECTED for P0)
**Why:** adds heavyweight runtime deps for rule enforcement that `ComplianceScorer` + a new deterministic `RuleEngine` already cover; the research brief itself flags micro-SaaS scale. Keep as P2 evaluation.

### Option D — Embed review SDK (Velt-class) (REJECTED)
**Why:** `ContentOpsStore` already implements the approval state machine; an SDK would replace tested code with an external dependency for a single-workspace product. Lean in-house wins (research risk #5).

### Chosen stack summary
- **API:** FastAPI 0.141.1 (existing) — new `src/routers/forge.py` (or per-module routers).
- **Persistence:** sqlite3 via the existing `ContentOpsStore`/`ContentPackageStore` pattern + new `BriefStore` in `src/forge/brief_store.py` (sync sqlite3, JSON columns, uuid hex ids, append-only audit). No new DB engine.
- **Deterministic engines (no LLM in the gate):** `ComplianceScorer` (blocked terms) + new `ChannelRuleEngine` (`src/forge/rule_engine.py`) + new `ClaimVerifier` (`src/forge/claims.py`, span-overlap + classification).
- **LLM adapter:** existing `src/services/llm_provider.py` only; drafting orchestration via extended `PlatformAdapter` + `ContentGenerator`.
- **Export:** pure functions in `src/forge/exporter.py` over the frozen approved snapshot; stdlib `difflib` for diffs; `src/services/jsonld_generator.py` for the AI-disclosure provenance block.
- **Zero new runtime deps for P0** (pydantic v2 already present). `guardrails-ai`/`fast-diff-match-patch` remain P2 candidates.

---

## 3. Prioritized Task List

### 3.0 Cross-cutting decisions (apply to ALL tasks)

- Channel id set (validated everywhere): `{"blog", "email", "linkedin", "x", "instagram", "landing", "script"}` — constant `FORGE_CHANNELS` in `src/forge/constants.py`.
- Claim classification enum (shared): `{"supported", "partially_supported", "unsupported", "opinion", "na"}` — `ClaimClassification` in `src/forge/claims.py`.
- Violation severity: `"hard"` (blocks approval/export unless excepted) | `"soft"` (warning only) — `RuleSeverity` in `src/forge/rule_engine.py`.
- Every store method that mutates workflow state appends an `audit_events` row via `_audit()`.
- Test files must not modify existing tests; new tests live in `tests/test_forge_*.py`.
- Git identity for pre-tester commits: `git config user.name "pre-tester" && git config user.email "pre-tester@local"`; developer: `"developer"`/`"developer@local"`.

### 3.1 P0-1 — Brief entity, persistence & validation (MVP FR-01, FR-06; US-001)

**Files:**
- `src/forge/__init__.py` (new, exports `FORGE_CHANNELS`)
- `src/forge/constants.py` (new) — `FORGE_CHANNELS: frozenset[str]`
- `src/forge/brief_store.py` (new) — `BriefStore` (sync sqlite3, follows `ContentOpsStore` pattern)
- `src/forge/brief_schemas.py` (new) — pydantic v2 request/response models

**Signatures (exact):**
```python
# src/forge/constants.py
FORGE_CHANNELS: frozenset[str] = frozenset({"blog", "email", "linkedin", "x", "instagram", "landing", "script"})

# src/forge/brief_schemas.py
class OutputConstraints(BaseModel):
    length: str = "medium"                      # short | medium | long
    tone: str = "professional"
    reading_level: str = "general"              # general | specialist
    keywords: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    hashtags: int | None = None                 # max hashtags for the channel

class BriefCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    audience: str = Field(..., min_length=1, max_length=2000)
    objective: str = Field(..., min_length=1, max_length=2000)
    offer: str = Field(..., min_length=1, max_length=2000)
    primary_cta: str = Field(..., min_length=1, max_length=500)
    language: str = "en"
    brand_profile_id: str | None = None
    channels: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)        # source refs: url | pasted text
    required_claims: list[str] = Field(default_factory=list)
    prohibited_phrases: list[str] = Field(default_factory=list)
    output_constraints: dict[str, OutputConstraints] = Field(default_factory=dict)  # key = channel

class Brief(BriefCreate):
    brief_id: str
    version: int = 1                       # immutable per save
    status: Literal["draft", "valid", "archived"] = "draft"
    created_by: str = "system"
    created_at: float

# src/forge/brief_store.py
class BriefStore:
    def __init__(self, path: str | Path) -> None: ...
    def create_brief(self, payload: BriefCreate, created_by: str = "system") -> Brief: ...
    def get_brief(self, brief_id: str) -> Brief: ...            # raises KeyError(brief_id) if missing
    def update_brief(self, brief_id: str, payload: BriefCreate, created_by: str) -> Brief: ...
        # bumps version += 1, returns NEW immutable version; old versions remain retrievable
    def versions(self, brief_id: str) -> list[Brief]: ...       # oldest → newest
    def validate(self, brief_id: str) -> dict: ...
        # {"valid": bool, "errors": [str], "warnings": [str]}
    def archive_brief(self, brief_id: str) -> None: ...
```

**Validation rules (P0, deterministic):**
- `channels` ⊆ `FORGE_CHANNELS`; empty → error `"channels_empty"`.
- `channels` non-empty AND `output_constraints` keys ⊆ `channels` → error `"output_constraints_channel_mismatch"`.
- `prohibited_phrases` entries non-empty; duplicates → warning `"duplicate_prohibited_phrase"`.
- `required_claims` non-empty entries.
- `brand_profile_id` may be null (no profile → default voice).

**Test expectations (pre-tester writes, developer makes green):**
```python
b = store.create_brief(BriefCreate(title="Launch", audience="CTOs", objective="...", offer="...", primary_cta="...", channels=["blog", "linkedin"]))
assert b.brief_id
assert b.version == 1
assert b.status == "draft"
assert store.get_brief(b.brief_id).title == "Launch"
b2 = store.update_brief(b.brief_id, BriefCreate(..., channels=["email"]), created_by="alice")
assert b2.version == 2
assert b.version == 1                      # old version immutable & retrievable
assert len(store.versions(b.brief_id)) == 2
assert store.get_brief(b.brief_id).channels == ["email"]   # get_brief returns LATEST
r = store.validate(b.brief_id)
assert r["valid"] is False and "channels_empty" in r["errors"]
with pytest.raises(KeyError):
    store.get_brief("nope")
```

**Execution order (numbered):**
1. `src/forge/constants.py` → 2. `src/forge/brief_schemas.py` → 3. `src/forge/brief_store.py` → 4. `tests/test_forge_brief_store.py` (pre-tester RED → developer GREEN) → 5. optional `src/routers/forge_briefs.py` wiring.

**Commit:** `feat(content-forge): add brief entity with versioned persistence` (pre-tester commit: `feat(tests): add content-forge P0 interface and behavioral tests`)

**Acceptance commands (guard-biztos form):**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_brief_store.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_brief_store.py
```

### 3.2 P0-2 — Drafting engine: ≥5 channels, brand-voice + per-channel rules (MVP FR-02, FR-03, FR-04; US-001)

**Files:**
- `src/forge/rule_engine.py` (new) — deterministic channel-rule enforcement
- `src/forge/drafting.py` (new) — orchestration (brief → per-channel drafts), calls `PlatformAdapter`/`ContentGenerator`/`llm_provider` + `ComplianceScorer` + `ChannelRuleEngine`
- `src/services/platform_adapter.py` (modify) — extend `PLATFORM_PROMPTS` to all 7 channels
- `src/forge/draft_schemas.py` (new) — pydantic models

**Signatures (exact):**
```python
# src/forge/rule_engine.py
class RuleSeverity(str, Enum):
    hard = "hard"
    soft = "soft"

class RuleViolation(BaseModel):
    rule_id: str                       # e.g. "channel.max_chars"
    channel: str
    severity: RuleSeverity
    message: str                       # names the violated rule + observed vs limit
    positions: list[tuple[int, int]] = Field(default_factory=list)  # char spans

class ChannelRuleResult(BaseModel):
    channel: str
    ok: bool                           # True iff no hard violations
    violations: list[RuleViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ChannelRuleEngine:
    def __init__(self, registry: ConstraintRegistry | None = None) -> None: ...
    def evaluate(self, channel: str, text: str, constraints: OutputConstraints | None = None,
                 prohibited_phrases: list[str] | None = None) -> ChannelRuleResult: ...
        # hard rules: channel char limit (registry), prohibited phrase hits, hashtag budget
        # soft rules: tone/reading-level keywords absent, required_sections missing
        # char limit: max_chars from registry; violated → "channel.max_chars" hard, message includes observed vs limit
        # prohibited phrase hit: "channel.prohibited_phrase" hard, positions = match spans
        # hashtag count > registry max_hashtags → "channel.max_hashtags" hard
        # required_sections missing → "channel.required_section" soft
        # reading_level keywords absent → "channel.reading_level" soft
    def evaluate_all(self, drafts: dict[str, str], brief: Brief) -> dict[str, ChannelRuleResult]: ...
        # key = channel; aggregate per-channel results; ok = all ok

# src/forge/drafting.py
class DraftResult(BaseModel):
    draft_id: str
    channel: str
    body: str
    brand_profile_id: str | None = None
    channel_rules_ok: bool
    rule_result: ChannelRuleResult
    compliance: dict                              # ComplianceResult model_dump()
    claims: list[dict] = Field(default_factory=list)   # placeholder until P0-3
    model_used: str
    created_at: float

async def generate_drafts(
    brief: Brief,
    channels: list[str] | None = None,            # None → brief.channels
    provider: Any | None = None,                  # injected LLM provider (tests pass a fake)
) -> dict[str, DraftResult]:
    """One draft per channel; raises ValueError on unknown channel; per-channel independent failure:
    a failed channel is reported (missing from dict → caller treats as failed) without blocking others."""
    ...

def _apply_brand_voice(system_prompt: str, profile: VoiceProfile | None) -> str: ...
    # appends profile.to_system_prompt() when profile present
```

**PlatformAdapter extension (exact):**
```python
PLATFORM_PROMPTS: dict[str, str]  # MUST contain keys for all 7: blog, email, linkedin, x, instagram, landing, script
# x: under 280 chars incl. hashtags; instagram: caption under 2200 chars, visible-cutoff 125, 3-8 hashtags;
# blog: long-form 800-2000 words, heading structure; landing: hero + benefits + CTA, under 1500 chars;
# script: short video script with scene/visual/audio lines, 60-90s
```

**Test expectations (pre-tester):**
```python
fake_provider = FakeProvider()   # returns canned text; exists in tests
drafts = await generate_drafts(brief, channels=["blog", "linkedin", "x"], provider=fake_provider)
assert set(drafts.keys()) == {"blog", "linkedin", "x"}
assert drafts["x"].channel == "x"
assert drafts["blog"].channel_rules_ok is True            # FakeProvider output respects limits
# long text violating char limit:
bad = await generate_drafts(brief_short, channels=["x"], provider=FakeProvider(text="y" * 400))
assert bad["x"].channel_rules_ok is False
assert any(v.rule_id == "channel.max_chars" and v.severity == RuleSeverity.hard for v in bad["x"].rule_result.violations)
# prohibited phrase hit:
hits = await generate_drafts(brief_with_prohibited, channels=["email"], provider=FakeProvider(text="Buy now today"))
assert any(v.rule_id == "channel.prohibited_phrase" and v.severity == RuleSeverity.hard for v in hits["email"].rule_result.violations)
# unknown channel:
with pytest.raises(ValueError):
    await generate_drafts(brief, channels=["tiktok"], provider=fake_provider)
# brand voice applied:
d = await generate_drafts(brief_with_profile, channels=["blog"], provider=RecordingProvider())
assert "Brand Voice" in d["blog"].model_used or "brand" in d["blog"].body.lower()  # recording provider proves injection
```

**Execution order (numbered):**
1. `src/forge/rule_engine.py` → 2. extend `src/services/platform_adapter.py` PLATFORM_PROMPTS → 3. `src/forge/drafting.py` → 4. `tests/test_forge_rule_engine.py` + `tests/test_forge_drafting.py` → 5. wire fake provider in tests/conftest.py (or per-file fixture).

**Commit:** `feat(content-forge): add multi-channel drafting engine with deterministic channel rules`

**Acceptance commands:**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_rule_engine.py tests/test_forge_drafting.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_rule_engine.py tests/test_forge_drafting.py
```

### 3.3 P0-3 — Claim verification & provenance (verified vs. suggestion) (MVP FR-18, FR-19, FR-20, FR-22; US-004)

**Files:**
- `src/forge/claims.py` (new) — classification + mechanical span-overlap verification
- `src/forge/claims_schemas.py` (new) — pydantic models

**Signatures (exact):**
```python
# src/forge/claims.py
class ClaimClassification(str, Enum):
    supported = "supported"
    partially_supported = "partially_supported"
    unsupported = "unsupported"
    opinion = "opinion"
    na = "na"

class Claim(BaseModel):
    claim_id: str
    text: str
    classification: ClaimClassification
    source_ref: str | None = None          # source url/title
    excerpt: str | None = None             # supporting chunk text
    span: tuple[int, int] | None = None    # [start, end) within excerpt
    source_date: str | None = None
    stale: bool = False                    # FR-20
    verified: bool = False                 # True iff classification == supported AND span overlaps excerpt

class ClaimVerifier:
    def __init__(self, overlap_ratio: float = 0.5) -> None: ...
    def verify_span(self, claim_text: str, excerpt: str, span: tuple[int, int] | None) -> bool: ...
        # MECHANICAL: when span is None → False; extracts excerpt[span[0]:span[1]] and
        # requires token-overlap(extracted, claim_text) >= overlap_ratio.
        # NEVER trusts model self-report — citation presence != correctness (research hint 3).
    def classify(self, text: str, source: str | None, judge: Callable[[str, str], str] | None = None) -> Claim:
        # judge: injected LLM-as-judge returning a ClaimClassification value; default deterministic:
        #   source None → "unsupported"; text starts with "I think"/"In my opinion" → "opinion";
        #   otherwise → "unsupported" (safe default). verified = (cls == supported and source) 
    def split_claims(self, text: str) -> list[str]: ...
        # sentence splitter on [.!?] + newline; returns non-empty trimmed sentences

class ProvenanceBlock(BaseModel):
    brief_id: str
    channel: str
    sources: list[dict]                    # [{url|ref, title, excerpt, span, date}]
    claims: list[Claim]
    generated_by_ai: bool = True           # EU AI Act Art. 50(2) marker (research risk #2)
    human_reviewed: bool = False           # flips True on approval (Art. 50(3) exemption)
```

**Test expectations (pre-tester):**
```python
v = ClaimVerifier()
assert v.verify_span("Acme raised $10M", "Acme raised $10M in Series B", (0, 16)) is True
assert v.verify_span("Acme raised $10M", "Acme raised $10M in Series B", (20, 30)) is False   # span outside
assert v.verify_span("Acme raised $10M", "Unrelated text here", None) is False                 # no span → never trusted
c = v.classify("Acme raised $10M", source="https://example.com/round")
assert c.classification == ClaimClassification.unsupported        # no judge → safe default
c2 = v.classify("I think this is great", source=None)
assert c2.classification == ClaimClassification.opinion
c3 = v.classify("Acme raised $10M", source="https://example.com/round",
                judge=lambda text, src: ClaimClassification.supported.value)
assert c3.verified is True
claims = v.split_claims("First sentence. Second one!\nThird")
assert claims == ["First sentence.", "Second one!", "Third"]
```

**Execution order (numbered):**
1. `src/forge/claims_schemas.py` → 2. `src/forge/claims.py` → 3. `tests/test_forge_claims.py` → 4. (P1) wire `split_claims` + `classify` into drafting pipeline.

**Commit:** `feat(content-forge): add claim verification and provenance model`

**Acceptance commands:**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_claims.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_claims.py
```

### 3.4 P0-4 — Blocked-term enforcement (hard gate + exception) (MVP FR-09; US-002)

**Files:**
- `src/forge/blocked_terms.py` (new) — gate over `ComplianceScorer`
- `src/forge/rule_engine.py` (modify, P0-2) — `ChannelRuleEngine.evaluate` already emits `channel.prohibited_phrase` hard violations; blocked-terms gate consumes those

**Signatures (exact):**
```python
# src/forge/blocked_terms.py
class BlockedTermGate:
    def __init__(self, scorer: ComplianceScorer | None = None) -> None:
        # scorer defaults to ComplianceScorer(VoiceProfile(vocabulary=VocabularyRules(banned=[...])))
    def scan(self, text: str, prohibited: list[str]) -> list[dict]:
        # returns [{"term": t, "positions": [(start, end), ...], "severity": "hard"}]
        # case-insensitive whole-word regex match; duplicates in `prohibited` collapsed
    def gate_approval(self, text: str, prohibited: list[str], exceptions: list[str] | None = None) -> dict:
        # {"blocked": bool, "hits": [dict], "excepted": [dict]}
        # hits whose term ∈ exceptions → moved to `excepted`, do NOT block
    def apply_exception(self, term: str, reviewer: str, reason: str) -> dict:
        # append-only record: {"term": term, "reviewer": reviewer, "reason": reason, "at": float}
```

**Test expectations (pre-tester):**
```python
g = BlockedTermGate()
hits = g.scan("Buy now and save big. Guaranteed results.", ["buy now", "guaranteed"])
assert [h["term"] for h in hits] == ["buy now", "guaranteed"]
assert all(h["severity"] == "hard" for h in hits)
assert g.scan("The offer is valid until Friday.", ["buy now"]) == []   # no false positive
r = g.gate_approval("Buy now to win.", ["buy now"], exceptions=["buy now"])
assert r["blocked"] is False and len(r["excepted"]) == 1
r2 = g.gate_approval("Buy now to win.", ["buy now"])
assert r2["blocked"] is True and len(r2["hits"]) == 1
```

**Execution order (numbered):**
1. `src/forge/blocked_terms.py` → 2. `tests/test_forge_blocked_terms.py` → 3. (P1) gate wiring into approval endpoint.

**Commit:** `feat(content-forge): add blocked-term approval gate with reviewer exceptions`

**Acceptance commands:**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_blocked_terms.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_blocked_terms.py
```

### 3.5 P0-5 — Review/approval workflow + review decision + version diff (MVP FR-12, FR-14, FR-15, FR-16, FR-17; US-003)

**Files:**
- `src/forge/review.py` (new) — thin adapter over `ContentOpsStore` approval machine + diff
- `src/forge/review_schemas.py` (new) — pydantic models

**Reuse (do NOT rebuild):** `ContentOpsStore.request_asset_approval`, `decide_asset_approval` (revision-bound, stale-decision rejection `APPROVAL_REVISION_STALE`, `SUPERSEDED` on edit-after-approval), `save_revision` (optimistic concurrency `ASSET_VERSION_CONFLICT`), `audit_events`. Tests exist: `tests/test_approval_workflow_v012.py`.

**Signatures (exact):**
```python
# src/forge/review.py
class ReviewDecision(str, Enum):
    approved = "APPROVED"
    rejected = "REJECTED"
    needs_changes = "NEEDS_CHANGES"

class ReviewRequest(BaseModel):
    draft_id: str
    requester: str
    risk: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    findings: list[str] = Field(default_factory=list)

class ReviewOutcome(BaseModel):
    decision_id: str
    draft_id: str
    decision: ReviewDecision
    reviewer: str
    reason: str
    version_hash: str            # sha256 of the locked approved body

class ReviewWorkflow:
    def __init__(self, store: ContentOpsStore) -> None: ...
    def request(self, req: ReviewRequest) -> str: ...            # returns request_id; binds current revision
    def decide(self, request_id: str, reviewer: str, decision: ReviewDecision, reason: str) -> ReviewOutcome: ...
        # blocks when: blocked-term gate blocked, or unsupported material claims exist (FR-22),
        # or open required-change findings (FR-15) → raises ValueError("APPROVAL_BLOCKED")
    def diff(self, draft_id: str, v1: int, v2: int) -> dict:
        # {"v1": int, "v2": int, "unified": str, "added": [str], "removed": [str], "meta": {...}}
        # unified = difflib.unified_diff(v1_content.splitlines(), v2_content.splitlines(), lineterm="")
    def versions(self, draft_id: str) -> list[dict]: ...          # delegate to store.revisions()
    def revoke(self, draft_id: str) -> None: ...                  # explicit revocation (FR-17 complement)
```

**Test expectations (pre-tester):**
```python
store = ContentOpsStore(tmp_path / "ops.db")
campaign = store.create_campaign("Launch", ["linkedin"], brief="...")
asset = store.create_asset(campaign, "linkedin", "Draft v1", "Launch post", author="alice")
wf = ReviewWorkflow(store)
rid = wf.request(ReviewRequest(draft_id=asset, requester="alice"))
out = wf.decide(rid, reviewer="bob", decision=ReviewDecision.approved, reason="OK")
assert out.decision == ReviewDecision.approved
assert out.version_hash == hashlib.sha256("Draft v1".encode()).hexdigest()
assert store.asset(asset)["state"] == "APPROVED"
store.save_revision(asset, "Draft v2", expected_version=1, author="alice")
assert store.asset(asset)["state"] == "IN_EDITING"          # FR-17: edit invalidates approval
d = wf.diff(asset, 1, 2)
assert "Draft v1" in d["unified"] and "Draft v2" in d["unified"]
assert len(wf.versions(asset)) == 2
# FR-15: decision blocked while findings unresolved:
rid2 = wf.request(ReviewRequest(draft_id=asset, requester="alice", findings=["Fix CTA"]))
with pytest.raises(ValueError, match="APPROVAL_BLOCKED"):
    wf.decide(rid2, reviewer="bob", decision=ReviewDecision.approved, reason="x")
```

**Execution order (numbered):**
1. `src/forge/review_schemas.py` → 2. `src/forge/review.py` → 3. `tests/test_forge_review.py` → 4. (P1) REST wiring.

**Commit:** `feat(content-forge): add review workflow adapter and version diff`

**Acceptance commands:**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_review.py tests/test_approval_workflow_v012.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_review.py
```

### 3.6 P0-6 — Export with byte-level fidelity (MVP FR-24, FR-25, FR-27; US-005)

**Files:**
- `src/forge/exporter.py` (new) — pure transforms over the frozen approved snapshot
- `src/forge/export_schemas.py` (new)

**Signatures (exact):**
```python
# src/forge/exporter.py
class ExportFormat(str, Enum):
    txt = "txt"
    md = "md"
    html = "html"
    json = "json"

class ExportRequest(BaseModel):
    draft_id: str
    approved_body: str               # frozen approved snapshot — export NEVER reads live state
    approved_hash: str               # sha256(approved_body) — must match store's locked hash
    channel: str
    format: ExportFormat
    include_provenance: bool = False
    include_disclosure: bool = True  # EU AI Act Art. 50(2) machine-readable marker (research risk #2)

class ExportResult(BaseModel):
    artifact_id: str
    filename: str                    # deterministic: f"{draft_id}-{channel}-{approved_hash[:8]}.{format}"
    content: str
    content_hash: str                # sha256 of `content`
    visible_fidelity: bool           # True iff body-extracted content == approved_body

class Exporter:
    def export(self, req: ExportRequest) -> ExportResult: ...
        # txt:  content == approved_body exactly (modulo trailing newline)
        # md:   markdown wrapper; extract body (strip wrapper) == approved_body
        # html: escape + <p> paragraphs; disclosure JSON-LD <script type="application/ld+json"> appended when include_disclosure
        # json: {"content": approved_body, "provenance": {...}, "ai_generated": true, ...}
        # visible_fidelity must be True in every case — golden test (research hint 10)
    def preflight(self, req: ExportRequest) -> dict:
        # {"ok": bool, "errors": [str], "warnings": [str]}
        # errors: hash mismatch (approved_hash != sha256(approved_body)), channel char limit exceeded
```

**Test expectations (pre-tester):**
```python
ex = Exporter()
body = "Announcing Acme 2.0 — now with AI workflows.\n\nLearn more at acme.com."
h = hashlib.sha256(body.encode()).hexdigest()
r = ex.export(ExportRequest(draft_id="d1", approved_body=body, approved_hash=h, channel="linkedin", format=ExportFormat.txt))
assert r.visible_fidelity is True
assert r.content.strip() == body          # byte-level: no silent alteration
assert r.filename == f"d1-linkedin-{h[:8]}.txt"
r_md = ex.export(ExportRequest(draft_id="d1", approved_body=body, approved_hash=h, channel="linkedin", format=ExportFormat.md))
assert r_md.visible_fidelity is True      # wrapper strips back to exact approved body
r_html = ex.export(..., format=ExportFormat.html, include_disclosure=True)
assert "application/ld+json" in r_html.content
assert "ai-generated" in r_html.content   # Art. 50(2) marker present
pf = ex.preflight(ExportRequest(draft_id="d1", approved_body=body, approved_hash="deadbeef", channel="x", format=ExportFormat.txt))
assert pf["ok"] is False and any("hash" in e for e in pf["errors"])
# export must never touch the store/draft — pure function over the snapshot:
assert store.asset(asset)["content"] == body   # unchanged after export
```

**Execution order (numbered):**
1. `src/forge/export_schemas.py` → 2. `src/forge/exporter.py` → 3. `tests/test_forge_exporter.py` → 4. (P1) REST wiring + CSV/copy export.

**Commit:** `feat(content-forge): add byte-faithful export with disclosure metadata`

**Acceptance commands:**
```bash
PATH="$PWD/.venv/bin:$PATH" python -m pytest tests/test_forge_exporter.py -q
PATH="$PWD/.venv/bin:$PATH" ruff check src/forge tests/test_forge_exporter.py
```

### 3.7 P1 backlog (next release — spec level only)

| Task | Notes |
|---|---|
| P1-1 REST wiring for P0 modules | `src/routers/forge_briefs.py`, `forge_drafts.py`, `forge_review.py`, `forge_exports.py`; FastAPI routers following `content_packages.py` error contract (400/404/409, JSON `{"detail": ...}`) |
| P1-2 Stale-source warnings in drafting | `Claim.source_date` vs configurable expiry; warning names affected claims (FR-20 end-to-end) |
| P1-3 Deterministic filenames + CSV/copy export | FR-26/FR-28; multi-artifact naming `package-channel-locale-version` |
| P1-4 Brand profile conflict detection | FR-08: `conflict_group` on ChannelRule; block publish on conflicts |
| P1-5 Profile permission enforcement | FR-11: role gate on profile endpoints |
| P1-6 Usage/cost/quality dashboard | FR-29..FR-32; reuses `src/services/analytics.py` |
| P1-7 Concurrent duplicate retry idempotency | FR-39: idempotency key + lock on package endpoints |

### 3.8 P2 backlog (later — spec level only)

| Task | Notes |
|---|---|
| P2-1 Retention & privacy policy | FR-33/FR-34: scheduled anonymization, audit intact |
| P2-2 Restricted-source enforcement | FR-21/FR-23: scope exclusion + attempt recording |
| P2-3 Guardrails-AI / NeMo integration evaluation | research hint 5 — only if P0 deterministic engines prove insufficient |
| P2-4 `fast-diff-match-patch` swap | only if difflib diff volume grows (research hint 8) |
| P2-5 Auto fact-check vs open web | explicitly out of MVP scope (product-scope §1.2) |

---

## 4. Acceptance Criteria (per P0 task)

| Task | Acceptance criteria |
|---|---|
| P0-1 Brief store | `create_brief`/`get_brief`/`update_brief`/`versions`/`validate`/`archive_brief` behave per test expectations; version bump immutability proven by test; `validate` catches `channels_empty` and channel-mismatch; all tests in `tests/test_forge_brief_store.py` green; ruff clean on `src/forge`. |
| P0-2 Drafting engine | All 7 channels in `PLATFORM_PROMPTS`; `generate_drafts` returns one DraftResult per requested channel; `channel_rules_ok` False with named hard violations (max_chars, prohibited_phrase, max_hashtags) when rules violated; unknown channel raises ValueError; brand-voice injection proven by recording provider; independent per-channel failure; tests green; ruff clean. |
| P0-3 Claims | `verify_span` mechanical overlap (no span → False, non-overlapping span → False); `classify` safe default unsupported/opinion; `split_claims` sentence splitter; tests green; ruff clean. |
| P0-4 Blocked terms | `scan` case-insensitive whole-word with positions + severity hard; no false positives; `gate_approval` blocked/excepted semantics; exception recording append-only; tests green; ruff clean. |
| P0-5 Review | state transitions approved→IN_EDITING on edit (FR-17), stale-decision rejection, diff unified with added/removed, version_hash = sha256(body), `APPROVAL_BLOCKED` on open findings; existing `test_approval_workflow_v012.py` still green; tests green; ruff clean. |
| P0-6 Export | `visible_fidelity` True for txt/md/html/json; `content.strip() == approved_body` for txt; JSON-LD `application/ld+json` + ai-generated marker in html when disclosure on; preflight catches hash mismatch + channel limit; export is a pure function (store untouched); tests green; ruff clean. |

**Global acceptance (M1 milestone, product-scope §5):** all six P0 suites green under the guard-biztos form; `ruff check src/forge tests/test_forge_*.py` clean; no existing test file modified.

---

## 5. Open Questions / Risks

1. **LLM availability in CI**: drafting tests MUST use injected fake providers (`FakeProvider`/`RecordingProvider` in tests) — never real API calls. Confirm the provider injection seam in `llm_provider.get_provider` supports a fake override (it returns a provider instance; tests pass their own).
2. **`ContentOpsStore` reuse boundary**: P0-5 wraps the existing approval machine. If a requirement needs a store schema change, prefer `ALTER TABLE` migrations in `ContentOpsStore.__init__` (existing pattern, see `campaign_columns` PRAGMA checks) over a new table.
3. **EU AI Act Art. 50** (in force 2 Aug 2026): export includes machine-readable AI marker by default; `human_reviewed` flips on approval (Art. 50(3) exemption path). FTC double-disclosure is a P1 UI concern (copy text guidance), not a P0 code gate.
4. **Rule drift**: char limits live in `src/constraints/data/registry.json` (date-stamped verification per research risk #4); do not hardcode limits in `rule_engine.py` — read from `ConstraintRegistry`.

---

*Validation note: spec-level artifact; per task instructions, no repo test suite was run (Budget guard). Formatting checked via file write + `wc -l`.*
