# Research Brief: Content-Forge — Brand-Safe Multi-Format AI Drafting, Review & Export

**Date:** 2026-08-14
**Task:** t_e60cffb1 (researcher) — upstream DISCOVERY for roadmap #1 (idea `brief-content-creation-20260813-1504`)
**Deliverable for:** analyst (t_bf3f4a8d) → tech-lead pipeline (root t_828d709c)
**Repo determination:** Content-Forge maps to the **dedicated implementation repo `/home/zoltan/contentforge`** (FastAPI + SQLAlchemy async + aiosqlite, v0.16.0, ~1200+ tests, origin `csaszarzoltan/contentforge`). Coordination artifacts (research briefs, analysis briefs, specs) live in the **micro-saas-lab monorepo `analysis/`** (project card `projects/content-forge.md`). This brief is committed to BOTH repos.

**Existing-repo reality check (read first — biggest wins are wiring, not building):**
ContentForge v0.16.0 already ships several pieces this roadmap item would otherwise rebuild:

| Capability | Already exists in contentforge |
|---|---|
| Brand voice profiles + prompt injection + **banned-term detection + compliance scoring** | `src/brand_voice/` (`VoiceProfile`, `PromptBinder`, `ComplianceScorer`, `VocabularyRules`, `compliance.py` — regex + readability + banned-term scoring) |
| Per-platform constraints (char limits, truncation, hashtags) | `src/constraints/` (`TextConstraints.max_chars`, `truncation_cutoff`, `max_hashtags`, registry loaded from `data/registry.json`) |
| Content generation across types w/ voice resolution | `src/services/generator.py` (`ContentGenerator.generate`, `GenerationResult.compliance_scores`) |
| Per-language prompt templates + character-budget warnings | `src/services/prompt_templates.py` (`LanguagePromptTemplate.character_budget_warning`) |
| Social connectors + rate limiting + publish | `src/connectors/`, `src/services/publish_service.py` (Twitter/X OAuth 1.0a 280-char truncation, LinkedIn OAuth 2.0) |
| A/B variants | `src/services/ab_service.py` |

**Gaps vs. the roadmap (what the research below targets):** grounded generation w/ source provenance (verified vs. suggestion), per-channel *rule* enforcement beyond char limits, review/approval workflow + version diff + audit, and export with byte-level fidelity. The draft engine is un-routed today: `generator.py` accepts only `{blog, social, email}` and emits a single blob — no per-channel adaptation, no claim-level annotations.

---

## 1. Trend Summary

1. **Grounded generation is table stakes, not a feature.** RAG- and retrieval-attributed generation (citations bound to retrieved passages) is the dominant pattern for reducing hallucination in writing tools; the research consensus (RAG survey, ATG/ReClaim line of work) is that conditioning on retrieved evidence with **per-sentence reference-claim interleaving** materially improves verifiability over bare prompting. Vendor APIs now ship grounding natively (OpenAI Responses API `web_search` tool with `url_citation` annotations; AWS Bedrock server-side grounding), which collapses the cost of adding citations.
2. **Citation presence ≠ citation correctness.** 2025-2026 evaluations (Nexumo's 11 tests, citation-verification papers) show models produce plausible-looking but fake citations. The emerging guardrail is *mechanical* verification: require cited spans to overlap retrieved chunks (interval arithmetic over `[file:start-end]` ranges), rather than trusting the model's self-report.
3. **Deterministic rule enforcement is moving out of the prompt and into code.** Brand-voice and channel constraints work best as **structured fields validated on write** (CMS-layer pattern), plus output-constraint libraries (Guardrails AI, NVIDIA NeMo Guardrails) that re-validate and repair LLM output against schema/validators after generation.
4. **Human-in-the-loop is a product layer, not an afterthought.** Review/approval infrastructure (inline comments anchored to content elements, explicit approval states, ownership routing, audit logs) is a recognized 4-6 week build; purpose-built SDKs (e.g. Velt) exist but are heavy for a micro-SaaS — a lean in-house state machine + version-diff is the right scale.
5. **Regulation is live and dates are concrete.** EU AI Act Art. 50 obligations for AI-generated content **apply from 2 August 2026** (machine-readable, detectable marking; disclosure of AI-generated text published to inform the public unless human review + editorial responsibility). FTC enforcement ("Operation AI Comply", "double disclosure" for AI-involved sponsored content) is bipartisan and active. Export must therefore carry disclosure metadata, not just fidelity.

---

## 2. Feature Candidates

### FC-1: Grounded drafting engine with claim-level citations and provenance
- **What:** Draft generator that takes source material (URLs/docs/paste), chunks + indexes it, and produces drafts where each factual claim carries a citation bound to a retrieved chunk (sentence-level `[source:N]` annotations), plus a machine-readable provenance block (source URL/title/span).
- **Why:** Core differentiator and de-risker: satisfies "preserve factual grounding and source provenance, distinguish verified claims from suggestions" in the roadmap; hallucination reduction is the #1 trust blocker for AI content tools (Arthur: RAG is "the single highest-leverage change").
- **Complexity:** high
- **Sources:**
  - https://arxiv.org/abs/2407.01796 (ReClaim: interleaved reference-claim generation for RAG, NAACL 2025)
  - https://www.arthur.ai/column/ai-guardrails-reduce-hallucinations
  - https://arxiv.org/html/2512.12117v1 (citation verification via interval arithmetic over retrieved chunks)
  - https://developers.openai.com/api/docs/guides/tools-web-search (native grounded web search + `url_citation` annotations)

### FC-2: Verified-claim vs. suggestion classification (claim verification stage)
- **What:** A post-generation pass that splits each draft sentence into (a) **verified** claims (entailed by a retrieved source chunk — NLI/entailment check or LLM-as-judge with source grounding) and (b) **suggestions** (model-generated, unsupported). Verified claims get `✅ source-cited`; suggestions get a visible "suggestion — verify before use" tag and are excluded from the "all claims sourced" export gate.
- **Why:** Directly implements the roadmap requirement to distinguish verified claims from suggestions; gives reviewers a trust surface and prevents export of unsourced factual claims.
- **Complexity:** medium-high (NLI models or a grounded LLM-as-judge pass)
- **Sources:**
  - https://arxiv.org/html/2410.01794v1 (Loki: open-source fact verification, NLI-based entailment ranking)
  - https://openfactcheck.com/ (OpenFactCheck: unified factuality evaluation framework)
  - https://github.com/jagilley/fact-checker (self-ask fact-checking pattern)

### FC-3: Deterministic blocked-terms / prohibited-phrase enforcement (post-generation validator)
- **What:** Regex + phrase-list validator run **after** generation (and before review), returning per-violation positions, severity, and a repair suggestion; also a hard export gate (blocked-term hits → export refused until resolved). Extends the existing `ComplianceScorer` banned-term detection from a score into an enforced gate.
- **Why:** "Prohibited phrases" is an explicit roadmap input; deterministic enforcement is cheap, auditable, and testable — no LLM involved in the gate itself.
- **Complexity:** low (extend existing `src/brand_voice/compliance.py`)
- **Sources:**
  - https://cyberax.com/ai-playbook/brand-voice-guardrails (banned phrases as explicit guardrails)
  - https://www.llmcms.org/guides/why-ai-brand-voice-tools-live-or-die-at-the-cms-layer (rules as validated-on-write fields)

### FC-4: Per-channel rule engine (constraints as code, not prose)
- **What:** A channel config object per target (blog, email, LinkedIn, X, Instagram, landing page, script) holding char limits, hashtag/mention budgets, emoji policy, paragraph/structure rules, CTA placement, and tone deltas — enforced in two layers: (1) prompt-level constraints injected at generation, (2) deterministic post-checks that fail with actionable errors (e.g. X >280 chars → auto-trim candidate + warning).
- **Why:** The roadmap demands per-channel constraints (280-char X limit, IG caption 2200/125-visible, LinkedIn 3000, blog/long-form); the existing `src/constraints/registry.json` already holds char/truncation data — this extends it with rule *types* and generation-time enforcement.
- **Complexity:** medium
- **Sources:**
  - https://blog.hootsuite.com/ideal-social-media-post-length/ (per-platform limits: IG 2,200, X 280/25k premium, LinkedIn 3,000, YouTube 5,000)
  - https://support.buffer.com/article/588-character-limits-for-each-social-network
  - https://typecount.com/blog/social-media-character-limits (14-platform table, verified Aug 2026)

### FC-5: Human-in-the-loop review/approval state machine + audit log
- **What:** Draft lifecycle: `draft → in_review → approved | changes_requested → (loop) → approved → exported`. Review actions (approve, request changes with inline notes, reject) are persisted as an append-only audit log (who/what/when/decision/notes). No downstream step (export, publish) runs on non-approved drafts.
- **Why:** Roadmap: "support human review and version comparison, and auditable approvals"; commercial value is "fewer review cycles" — the workflow must be explicit and testable.
- **Complexity:** medium
- **Sources:**
  - https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation
  - https://velt.dev/blog/how-to-add-human-review-ai-output (inline comments, approval states, ownership routing, audit trails)

### FC-6: Version history + side-by-side diff of drafts
- **What:** Every save/regenerate creates a version (content hash + full snapshot or diff-patch storage); reviewer sees unified diff between versions (difflib / google-diff-match-patch) and can compare approved-vs-current before export.
- **Why:** Roadmap: "version comparison"; diff is what makes review fast and export trustable.
- **Complexity:** low-medium
- **Sources:**
  - https://github.com/google/diff-match-patch (semantic diff/patch library, multi-language)
  - https://pypi.org/project/fast-diff-match-patch/ (Python wrapper over C++ impl)
  - https://docs.python.org/3/library/difflib.html (stdlib difflib — zero-dep baseline)

### FC-7: Export with byte-level fidelity + disclosure metadata
- **What:** Approved content is exported from the **approved snapshot only** — export reads the frozen approved version, never live state; export is a pure transformation (markdown/HTML/txt per channel) covered by golden tests asserting the exported bytes equal the approved content bytes modulo the wrapper; optional AI-disclosure footer and machine-readable provenance (JSON-LD / XMP / C2PA-style manifest) appended for EU AI Act Art. 50(2) marking.
- **Why:** Roadmap explicitly: "export approved content without silently changing it"; also the regulatory layer (see Risks).
- **Complexity:** medium
- **Sources:**
  - https://www.npmjs.com/package/draft-js-export-markdown (round-trip export of editor content — the pattern: serialize from canonical store)
  - https://github.com/Rosey/markdown-draft-js (DraftJS ↔ markdown, both directions — round-trip fidelity)
  - https://pypi.org/project/draftjs-exporter-markdown/ (Python-side Draft.js ContentState → markdown)
  - https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html (content-provenance manifest standard)

### FC-8: AI-disclosure helper (regulatory compliance assist)
- **What:** Configurable disclosure snippets (FTC "generated with AI" double-disclosure line, EU Art. 50(3) public-interest notice) injected into export templates per channel; flags drafts intended for public-interest publication where human review has NOT occurred (Art. 50(3) exemption requires human review + editorial responsibility).
- **Why:** Regulatory obligations are live (EU AI Act 2 Aug 2026; FTC enforcement ongoing); a compliance assist is cheap and sells trust.
- **Complexity:** low
- **Sources:**
  - https://artificialintelligenceact.eu/article/50/ (Art. 50 text, official OJ version) + https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
  - https://humanadsai.com/blog/ftc-ai-generated-content-disclosure and https://inbeat.agency/blog/ftc-guidelines-for-influencers (double disclosure)

---

## 3. Implementation Hints

**Grounding / provenance (FC-1, FC-2):**
1. **Chunk-then-cite pipeline:** `langchain` or plain `textwrap`/custom splitter → embeddings (sentence-transformers / `text-embedding-3-small`) → vector store (SQLite `sqlite-vec` or `chromadb` local; for a micro-SaaS, `sqlite-vec` keeps the aiosqlite pattern). Retrieved chunks become the only permitted citation corpus.
2. **ReClaim-style interleaving:** prompt the model to emit claim + `[src:N]` inline while generating (per-sentence attribution, per arxiv 2407.01796), instead of appending a bibliography at the end — per-sentence citations are far more verifiable.
3. **Mechanical citation verification:** post-check each `[src:N]` span against the retrieved chunk text (overlap / containment test — see arxiv 2512.12117v1 interval-arithmetic approach). Reject or downgrade drafts whose citations don't overlap retrieved chunks — never trust model self-report.
4. **Vendor-native grounding shortcut (P0/P1):** OpenAI Responses API `web_search` tool returns `url_citation` annotations (URL + title + span) — the cheapest provenance source if provider budget allows; keep the deterministic verifier (3) on top regardless.

**Brand-voice & channel rules (FC-3, FC-4):**
5. **Output-constraint library:** `guardrails-ai` (PyPI `guardrails-ai`) — pydantic-style validators + re-prompt on failure; or `nemoguardrails` (NVIDIA, Colang rails incl. fact-checking rails) for heavier guardrail needs. Both wrap the existing `ContentGenerator` with zero changes to the generation core.
6. **Structured rules, not prose:** keep brand-voice/channel rules as validated Pydantic fields (pattern already in `src/constraints/models.py` + `src/brand_voice/`) — deterministic validators run post-generation (`difflib`-independent regex/char checks); the CMS-layer essay (llmcms.org) shows rules fail validation on write rather than drifting.
7. **Per-channel registry extension:** add rule *types* to `src/constraints/data/registry.json` (hashtag budget, emoji policy, CTA position, structure template per channel); reuse existing `TextConstraints` (max_chars, truncation_cutoff, max_hashtags) — verify against Hootsuite/Buffer/TypeCount tables, not memory.

**Review / version-diff (FC-5, FC-6):**
8. **Diff & patch:** stdlib `difflib` for MVP (unified diff, zero deps); `fast-diff-match-patch` (PyPI) if diff volume grows (C++-speed semantic diffs, patch application for "restore version"). Store full snapshots + SHA-256 content hash per version (SQLite row); content-addressed version table makes "export this exact version" trivial.
9. **Review state machine:** explicit enum state transitions in code (`draft → in_review → approved|changes_requested`) with an append-only `review_events` table (actor, action, note, version_id, ts) — this is the audit trail; publish/export endpoints check state = approved before proceeding.

**Export fidelity (FC-7):**
10. **Approved-snapshot-only export + golden tests:** export functions take `version_id` (frozen approved content) and are pure transforms with golden-file tests (`assert exported_bytes == approved_bytes modulo wrapper`); never re-render from live draft state. Draft.js-style canonical-store → markdown round-trip (draft-js-export-markdown / draftjs-exporter-markdown) is the reference pattern for lossless serialization.
11. **Provenance metadata:** append JSON-LD (`application/ld+json` AI-generated marker) or C2PA-style manifest for machine-readable marking (EU AI Act Art. 50(2)); see spec.c2pa.org for the standard shape.

**Reference architectures / repo patterns:**
- Existing contentforge patterns to reuse: `ContentGenerator` orchestration (`src/services/generator.py`), `PromptBinder`/voice resolution (`src/brand_voice/`), `ConstraintRegistry` (`src/constraints/registry.py`), LLM provider abstraction (`src/services/llm_provider.py`).
- Follow the repo's TDD conventions (pytest + `pythonpath=["src"]`; tests in `tests/`), matching prior features (brand-kit architecture-spec pattern: model → schemas → router → storage → tests → docs).

---

## 4. Risks

1. **Citation hallucination despite grounding:** models emit plausible fake citations even with RAG (documented by Nexumo's 11 grounding tests and citation-verification literature). Mitigation: mechanical overlap verification of every citation span; never present unverified citations as sourced.
2. **Regulatory exposure — EU AI Act Art. 50 (in force 2 Aug 2026):** providers of AI systems generating text must ensure outputs are **marked machine-readable and detectable as AI-generated** (Art. 50(2), with an assistive-editing exemption); deployers publishing AI-generated text informing the public must disclose it **unless** the content underwent human review/editorial control with a responsible natural/legal person (Art. 50(3)). FTC: "Operation AI Comply" enforcement and the double-disclosure expectation for AI-involved sponsored content are active; penalties reach ~$53k/violation. Export paths that strip disclosure metadata or auto-publish unreviewed drafts are the two highest-liability flows.
3. **Export fidelity regressions:** any export path that re-renders from live state (rather than the approved snapshot) silently mutates approved content — the exact failure the roadmap forbids. Golden tests + frozen-version exports are the guard.
4. **Rule drift:** char limits change (X premium 25k, IG visible-cutoff 125); hardcoded limits rot. Source the per-channel registry from maintained tables and date-stamp verifications.
5. **Scope creep in P0:** don't build a full CMS/editor; lean in-house review state machine + difflib diff beats embedding heavy review SDKs (Velt-class) for a micro-SaaS.

---

## 5. Source Links

**Grounded generation / provenance**
- https://arxiv.org/abs/2407.01796 — Ground Every Sentence (ReClaim, NAACL 2025)
- https://arxiv.org/pdf/2410.12837 — Comprehensive RAG survey
- https://www.arthur.ai/column/ai-guardrails-reduce-hallucinations — RAG as hallucination guardrail
- https://arxiv.org/html/2512.12117v1 — citation verification via interval arithmetic
- https://developers.openai.com/api/docs/guides/tools-web-search — OpenAI web_search tool + url_citation annotations
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/web-search — Azure OpenAI grounding (cross-check)
- https://medium.com/@Nexumo_/rag-grounding-11-tests-that-expose-fake-citations-30d84140831a — fake-citation failure modes
- https://www.mdpi.com/2504-2289/9/12/320 — RAG systematic review (provenance attribution)

**Claim verification**
- https://arxiv.org/html/2410.01794v1 — Loki fact-verification tool (NLI-based)
- https://openfactcheck.com/ — OpenFactCheck framework
- https://github.com/jagilley/fact-checker — self-ask fact-checking

**Brand voice / channel rules / guardrails**
- https://www.llmcms.org/guides/why-ai-brand-voice-tools-live-or-die-at-the-cms-layer — rules as structured fields
- https://cyberax.com/ai-playbook/brand-voice-guardrails — banned phrases, tone calibration
- https://www.contentful.com/blog/llm-guardrails/ — structured brand input at prompt layer
- https://www.glean.com/perspectives/how-to-create-a-brand-voice-guide-for-ai-tools — voice guide as retrievable rules
- https://github.com/NVIDIA-NeMo/Guardrails — NeMo Guardrails (Colang, fact-check rails)
- https://docs.nvidia.com/nemo/guardrails/latest/index.html — NeMo Guardrails docs
- https://pypi.org/project/guardrails-ai/0.1.5/ — Guardrails AI (pydantic-style output validation)
- https://blog.hootsuite.com/ideal-social-media-post-length/ — per-platform char limits
- https://support.buffer.com/article/588-character-limits-for-each-social-network — Buffer limits (cross-check)
- https://typecount.com/blog/social-media-character-limits — 14-platform table verified 2026

**Review / approval / version-diff**
- https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation — HITL approval design
- https://velt.dev/blog/how-to-add-human-review-ai-output — review infra (comments, states, audit)
- https://github.com/google/diff-match-patch — diff/patch library
- https://pypi.org/project/fast-diff-match-patch/ — Python C++-speed wrapper
- https://docs.python.org/3/library/difflib.html — stdlib difflib

**Export fidelity**
- https://www.npmjs.com/package/draft-js-export-markdown — canonical-store → markdown export
- https://github.com/Rosey/markdown-draft-js — DraftJS ↔ markdown round-trip
- https://pypi.org/project/draftjs-exporter-markdown/ — Python Draft.js ContentState → markdown
- https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html — C2PA provenance manifest

**Regulatory (FTC / EU AI Act / provenance standards)**
- https://artificialintelligenceact.eu/article/50/ — Article 50 full text (OJ version)
- https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act — EC FAQ (timeline, 2 Aug 2026)
- https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content — Code of Practice on transparency
- https://www.ftc.gov/ai — FTC AI Compliance Plan
- https://humanadsai.com/blog/ftc-ai-generated-content-disclosure — FTC double-disclosure interpretation
- https://inbeat.agency/blog/ftc-guidelines-for-influencers — double disclosure guidance
- https://www.acc.com/sites/default/files/program-materials/upload/FTC-Crackdown-on-Influencers-Holland-and-Hart_0.pdf — Operation AI Comply enforcement overview
- https://c2pa.ai/vs-watermarking — machine-readable labelling vs watermarking

**Repo-local references**
- `/home/zoltan/contentforge` — implementation repo (HEAD 7ea067e, v0.16.0): `src/brand_voice/`, `src/constraints/`, `src/services/generator.py`, `src/services/prompt_templates.py`, `src/connectors/`, `src/services/publish_service.py`
- `/home/zoltan/micro-saas-lab/projects/content-forge.md` — project card; `analysis/analysis-brief.md` — prior content-creation pipeline analysis (US-001)
