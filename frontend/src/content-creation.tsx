/* ── Content Creation — 4-step cross-platform wizard ────────
   P0-6 (US-001..US-004) per analysis-brief.md (t_ef548473).
   Turn one source asset into a consistent cross-platform content
   package: LinkedIn / Twitter / Email / Blog variants.

   The wizard mirrors transcreation.tsx conventions: typed API
   contract header, apiMessage()/validationMessage reuse, hash
   routing via navigation.ts ("content-creation" route).

   API contract (src/routers/content_packages.py, /api/v1/content-packages):
     POST /api/v1/content-packages
          header: Idempotency-Key: <string> (required)
          body: {source_type, source_ref, platforms, brand_voice_id?}
     GET  /api/v1/content-packages/{id}
     POST /api/v1/content-packages/{id}/generate
     POST /api/v1/content-packages/{id}/validate
     POST /api/v1/content-packages/{id}/approve
     POST /api/v1/content-packages/{id}/publish
          header: Idempotency-Key: <string> (required)
     GET  /api/v1/content-packages/{id}/history
   ─────────────────────────────────────────────────────────── */

import React, {useEffect, useState} from "react";
import {validationMessage} from "./flow";

/* ── types (mirror src/schemas/content_packages.py) ──────── */

export type ContentSourceType = "generation_id" | "text" | "url";
export type ContentPackageState =
  | "draft" | "generating" | "validating" | "ready_to_approve"
  | "approved" | "publishing" | "published" | "failed";
export type ContentVariantState = "pending" | "generated" | "validated" | "published" | "failed";

export type ContentVariant = {
  id: string;
  platform: string;
  content: string;
  char_count: number;
  validation_status: ContentVariantState;
  publish_status: ContentVariantState;
  error?: string | null;
  remote_id?: string | null;
};

export type ContentPackage = {
  id: string;
  source_type: ContentSourceType;
  source_ref: string;
  state: ContentPackageState;
  brand_voice_id: string | null;
  platforms: string[];
  variants: ContentVariant[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type ContentPackageCreated = {
  id: string;
  state: ContentPackageState;
  platforms: string[];
  created_at?: number | null;
};

/* ── step props (4-step wizard contract) ─────────────────── */

export type StepProps = {
  onNext: () => void;
  onBack?: () => void;
  packageId?: string | null;
  onPackageCreated?: (id: string) => void;
};

/* ── API helpers ─────────────────────────────────────────── */

/* Surface the real API detail (e.g. 409 wrong-state) instead of the
   generic fallback; falls back to the friendly message for non-API errors. */
function apiMessage(x: unknown): string {
  if (x instanceof Error) {
    try {
      const parsed = JSON.parse(x.message) as {detail?: unknown};
      if (parsed && typeof parsed.detail === "string") return parsed.detail;
    } catch {
      /* not a JSON error body — use the raw message */
    }
    return x.message;
  }
  return validationMessage(x);
}

async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {"Content-Type": "application/json", ...(options?.headers || {})},
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

const IDEM_KEY = (): string => `cp-${Date.now()}-${Math.random().toString(36).slice(2)}`;

export async function createContentPackage(input: {
  source_type: ContentSourceType;
  source_ref: string;
  platforms: string[];
  brand_voice_id?: string | null;
  idempotencyKey: string;
}): Promise<ContentPackageCreated> {
  return apiRequest<ContentPackageCreated>("/api/v1/content-packages", {
    method: "POST",
    headers: {"Idempotency-Key": input.idempotencyKey},
    body: JSON.stringify({
      source_type: input.source_type,
      source_ref: input.source_ref,
      platforms: input.platforms,
      brand_voice_id: input.brand_voice_id,
    }),
  });
}

export async function getContentPackage(packageId: string): Promise<ContentPackage> {
  return apiRequest<ContentPackage>(`/api/v1/content-packages/${packageId}`);
}

export async function generatePackage(packageId: string): Promise<{state: string; variant_count: number}> {
  return apiRequest(`/api/v1/content-packages/${packageId}/generate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function validatePackage(packageId: string): Promise<{state: string; variants: unknown[]}> {
  return apiRequest(`/api/v1/content-packages/${packageId}/validate`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function approvePackage(packageId: string): Promise<{state: string}> {
  return apiRequest(`/api/v1/content-packages/${packageId}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function publishPackage(packageId: string, idempotencyKey: string): Promise<{state: string; deliveries: unknown[]}> {
  return apiRequest(`/api/v1/content-packages/${packageId}/publish`, {
    method: "POST",
    headers: {"Idempotency-Key": idempotencyKey},
    body: JSON.stringify({}),
  });
}

/* ── presentation helpers ────────────────────────────────── */

const PLATFORM_OPTIONS = [
  {value: "linkedin", label: "LinkedIn"},
  {value: "twitter", label: "Twitter / X"},
  {value: "email", label: "Email"},
  {value: "blog", label: "Blog"},
];

const pretty = (v: unknown): string =>
  String(v ?? "").replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());

/* ── shared wizard chrome ────────────────────────────────── */

function StepHeader({step, title}: {step: number; title: string}) {
  return (
    <header className="page-head">
      <span className="eyebrow">CONTENT CREATION</span>
      <h1>Content packages</h1>
      <p>
        {step}. {title}
      </p>
    </header>
  );
}

function StepNav({onBack, onNext, nextLabel = "Next", canNext = true}: StepProps & {nextLabel?: string; canNext?: boolean}) {
  return (
    <footer className="v-step-nav">
      {onBack && (
        <button type="button" className="ghost" onClick={onBack}>
          ← Back
        </button>
      )}
      <button type="button" disabled={!canNext} onClick={onNext}>
        {nextLabel}
      </button>
    </footer>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 1 — Select Source (library/paste + platforms + voice)
   ═══════════════════════════════════════════════════════════ */

export function ContentStepSource(props: StepProps): React.ReactElement {
  const [mode, setMode] = useState<ContentSourceType>("text");
  const [sourceRef, setSourceRef] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["linkedin", "twitter"]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const valid = sourceRef.trim().length > 0 && platforms.length > 0;

  const togglePlatform = (p: string) =>
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));

  const handleNext = () => {
    if (!valid || busy) return;
    props.onNext();
    setBusy(true);
    setError("");
    createContentPackage({
      source_type: mode,
      source_ref: sourceRef.trim(),
      platforms,
      brand_voice_id: null,
      idempotencyKey: IDEM_KEY(),
    })
      .then((created) => {
        if (typeof props.onPackageCreated === "function") {
          props.onPackageCreated(created.id);
        }
      })
      .catch((x) => setError(apiMessage(x)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="panel">
      <StepHeader step={1} title="Select your source asset" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <label className="v-field">
        Source type
        <select value={mode} onChange={(e) => setMode(e.target.value as ContentSourceType)}>
          <option value="text">Paste text</option>
          <option value="generation_id">Blog generation id</option>
          <option value="url">URL</option>
        </select>
      </label>
      <label className="v-field">
        Source asset
        <textarea
          aria-label="Source asset"
          value={sourceRef}
          onChange={(e) => setSourceRef(e.target.value)}
          placeholder="Paste the blog post, draft, or URL you want to turn into a cross-platform package…"
          rows={6}
        />
      </label>
      <fieldset className="v-field">
        <legend>Target platforms</legend>
        <div className="cp-platforms">
          {PLATFORM_OPTIONS.map((p) => (
            <label key={p.value} className="cp-platform">
              <input
                type="checkbox"
                aria-label={`Platform ${p.label}`}
                checked={platforms.includes(p.value)}
                onChange={() => togglePlatform(p.value)}
              />
              {p.label}
            </label>
          ))}
        </div>
      </fieldset>
      <StepNav onNext={handleNext} canNext={valid && !busy} />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 2 — Configure & Generate (per-platform progress)
   ═══════════════════════════════════════════════════════════ */

export function ContentStepGenerate(props: StepProps): React.ReactElement {
  const [pkg, setPkg] = useState<ContentPackage | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [state, setState] = useState<string>("");

  const load = () => {
    if (!props.packageId) return;
    getContentPackage(props.packageId)
      .then(setPkg)
      .catch((x) => setError(apiMessage(x)));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.packageId]);

  const generate = () => {
    if (!props.packageId) return;
    setBusy(true);
    setError("");
    generatePackage(props.packageId)
      .then((r) => setState(r.state))
      .catch((x) => setError(apiMessage(x)))
      .finally(() => {
        setBusy(false);
        setTimeout(load, 300);
      });
  };

  const allGenerated =
    pkg !== null &&
    pkg.variants.length > 0 &&
    pkg.variants.every((v) => v.validation_status === "generated" || v.validation_status === "validated");

  return (
    <section className="panel">
      <StepHeader step={2} title="Configure & generate platform variants" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <div className="v-field">
        <button type="button" onClick={generate} disabled={busy || !props.packageId}>
          {busy ? "Generating…" : "Generate variants"}
        </button>
        {state && <p className="muted">Pipeline state: {pretty(state)}</p>}
      </div>
      {pkg && (
        <div className="cp-cards">
          {pkg.variants.map((v) => (
            <article className="cp-card" key={v.id}>
              <h3>{pretty(v.platform)}</h3>
              <p className="muted">
                {v.char_count} chars · {pretty(v.validation_status)}
              </p>
              <small className="cp-content">{v.content.slice(0, 180)}</small>
            </article>
          ))}
        </div>
      )}
      <StepNav onBack={props.onBack} onNext={props.onNext} nextLabel="Next" canNext={allGenerated} />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 3 — Review & Validate (constraint badges + approve)
   ═══════════════════════════════════════════════════════════ */

export function ContentStepValidate(props: StepProps): React.ReactElement {
  const [pkg, setPkg] = useState<ContentPackage | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [validated, setValidated] = useState(false);

  const load = () => {
    if (!props.packageId) return;
    getContentPackage(props.packageId)
      .then(setPkg)
      .catch((x) => setError(apiMessage(x)));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.packageId]);

  const runValidate = () => {
    if (!props.packageId) return;
    setBusy(true);
    setError("");
    validatePackage(props.packageId)
      .then(() => setValidated(true))
      .catch((x) => setError(apiMessage(x)))
      .finally(() => {
        setBusy(false);
        setTimeout(load, 300);
      });
  };

  const approve = () => {
    if (!props.packageId) return;
    setBusy(true);
    setError("");
    approvePackage(props.packageId)
      .then(() => {
        setValidated(true);
        props.onNext();
      })
      .catch((x) => setError(apiMessage(x)))
      .finally(() => setBusy(false));
  };

  const allValidated =
    pkg !== null &&
    pkg.variants.length > 0 &&
    pkg.variants.every((v) => v.validation_status === "validated");

  return (
    <section className="panel">
      <StepHeader step={3} title="Review & validate variants" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <div className="v-field">
        <button type="button" onClick={runValidate} disabled={busy || !props.packageId}>
          {busy ? "Validating…" : "Validate against platform rules"}
        </button>
      </div>
      {pkg && (
        <div className="cp-cards">
          {pkg.variants.map((v) => (
            <article className="cp-card" key={v.id}>
              <h3>
                {pretty(v.platform)}
                <span className={`risk-pill ${v.validation_status === "validated" ? "risk-low" : "risk-medium"}`}>
                  {pretty(v.validation_status)}
                </span>
              </h3>
              <p className="muted">
                {v.char_count} chars
                {v.error ? ` · ${v.error}` : ""}
              </p>
              <small className="cp-content">{v.content.slice(0, 180)}</small>
            </article>
          ))}
        </div>
      )}
      <StepNav
        onBack={props.onBack}
        onNext={approve}
        nextLabel="Approve"
        canNext={(validated || allValidated) && !busy}
      />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 4 — Publish & Track
   ═══════════════════════════════════════════════════════════ */

export function ContentStepPublish(props: StepProps): React.ReactElement {
  const [pkg, setPkg] = useState<ContentPackage | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{state: string; deliveries: unknown[]} | null>(null);

  const load = () => {
    if (!props.packageId) return;
    getContentPackage(props.packageId)
      .then(setPkg)
      .catch((x) => setError(apiMessage(x)));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.packageId]);

  const publish = () => {
    if (!props.packageId) return;
    setBusy(true);
    setError("");
    publishPackage(props.packageId, IDEM_KEY())
      .then((r) => {
        setResult(r);
        setTimeout(load, 300);
      })
      .catch((x) => setError(apiMessage(x)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="panel">
      <StepHeader step={4} title="Publish & track" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <div className="v-field">
        <button type="button" onClick={publish} disabled={busy || !props.packageId}>
          {busy ? "Publishing…" : "Publish approved variants"}
        </button>
        {result && (
          <p className="muted">
            State: {pretty(result.state)} · {result.deliveries.length} deliveries
          </p>
        )}
      </div>
      {pkg && (
        <div className="cp-cards">
          {pkg.variants.map((v) => (
            <article className="cp-card" key={v.id}>
              <h3>
                {pretty(v.platform)}
                <span className={`risk-pill ${v.publish_status === "published" ? "risk-low" : "risk-medium"}`}>
                  {pretty(v.publish_status)}
                </span>
              </h3>
              {v.remote_id && <small className="muted">remote: {v.remote_id}</small>}
              {v.error && <small className="muted">{v.error}</small>}
            </article>
          ))}
        </div>
      )}
      <StepNav onBack={props.onBack} onNext={props.onNext} nextLabel="Done" />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   ContentCreationWizard — 4-step flow (US-001..US-004)
   ═══════════════════════════════════════════════════════════ */

export function ContentCreationWizard(): React.ReactElement {
  const [step, setStep] = useState(1);
  const [packageId, setPackageId] = useState<string | null>(null);

  const next = () => setStep((s) => Math.min(4, s + 1));
  const back = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div className="v-wizard">
      <div className="v-steps" role="progressbar" aria-valuemin={1} aria-valuemax={4} aria-valuenow={step}>
        {[1, 2, 3, 4].map((n) => (
          <span key={n} className={`v-step-dot${n === step ? " active" : ""}${n < step ? " done" : ""}`}>
            {n}
          </span>
        ))}
        <span className="muted">Step {step} of 4</span>
        <button type="button" className="ghost v-back" onClick={back} disabled={step === 1}>
          ← Back
        </button>
      </div>
      {step === 1 && <ContentStepSource onNext={next} onPackageCreated={setPackageId} />}
      {step === 2 && (
        <ContentStepGenerate onNext={next} onBack={back} packageId={packageId} />
      )}
      {step === 3 && (
        <ContentStepValidate onNext={next} onBack={back} packageId={packageId} />
      )}
      {step === 4 && <ContentStepPublish onNext={next} onBack={back} packageId={packageId} />}
    </div>
  );
}
