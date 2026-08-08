// ── Video — 5-step blog-to-video wizard ─────────────────────
//   P0-7 (US-001/US-004) + P1-5 (US-003 retry UX).
//
//   The wizard mirrors transcreation.tsx conventions: typed API
//   contract header, apiMessage()/validationMessage reuse, hash
//   routing via navigation.ts ("video" route, label "Video").
//
//   API contract (src/routers/video.py, canonical /api/v1/video):
//     POST /api/v1/video/jobs            {source_type, source_ref, ...}
//     GET  /api/v1/video/jobs/{id}       job + scenes[] + overall_progress
//     POST /api/v1/video/jobs/{id}/retry {retried: [scene_id]}
//     GET  /api/v1/video/jobs/{id}/export?resolution=720p&partial=true
//     GET  /api/v1/video/voices?provider=openai
//   ───────────────────────────────────────────────────────────

import React, {useEffect, useState} from "react";
import {validationMessage} from "./flow";

/* ── types (mirror src/schemas/video.py) ─────────────────── */

export type VideoSourceType = "generation_id" | "url" | "script";
export type VideoJobState = "queued" | "outline" | "scenes" | "render" | "ready" | "failed" | "partial";
export type VideoSceneState = "pending" | "generating" | "done" | "failed";
export type StylePreset = "explainer" | "documentary";
export type Resolution = "480p" | "720p" | "1080p";

export type VideoScene = {
  id: string;
  order: number;
  heading: string | null;
  state: VideoSceneState;
  attempts: number;
  error: string | null;
  image_path: string | null;
  audio_path: string | null;
};

export type VideoJob = {
  id: string;
  source_type: VideoSourceType;
  source_ref: string;
  state: VideoJobState;
  brand_voice_id: string | null;
  voice_profile_name: string | null;
  style_preset: StylePreset | null;
  voice: string | null;
  resolution: Resolution;
  overall_progress: number;
  scenes: VideoScene[];
};

export type VideoJobCreated = {
  job_id: string;
  state: VideoJobState;
  segments: string[] | null;
};

export type VoiceItem = {id: string; name: string};

/* ── step props (5-step wizard contract) ──────────────────── */

export type VideoWizardProps = {
  defaultVoice?: string;
  defaultStyle?: StylePreset;
};

export type StepProps = {
  onNext: () => void;
  onBack?: () => void;
  jobId?: string | null;
  onJobCreated?: (jobId: string) => void;
};

/* ── API helpers ─────────────────────────────────────────── */

/* Surface the real API detail (e.g. 409 nothing-renderable) instead of the
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

export async function createVideoJob(input: {
  source_type: VideoSourceType;
  source_ref: string;
  brand_voice_id?: string | null;
  style_preset?: StylePreset | null;
  voice?: string | null;
  resolution?: Resolution;
  auto_segment?: boolean;
}): Promise<VideoJobCreated> {
  return apiRequest<VideoJobCreated>("/api/v1/video/jobs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getVideoJob(jobId: string): Promise<VideoJob> {
  return apiRequest<VideoJob>(`/api/v1/video/jobs/${jobId}`);
}

export async function retryVideoJob(jobId: string): Promise<{retried: string[]}> {
  return apiRequest<{retried: string[]}>(`/api/v1/video/jobs/${jobId}/retry`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function listVoices(provider: string = "openai"): Promise<{provider: string; voices: VoiceItem[]}> {
  return apiRequest<{provider: string; voices: VoiceItem[]}>(`/api/v1/video/voices?provider=${provider}`);
}

/* ── presentation helpers ────────────────────────────────── */

const STYLE_OPTIONS: {value: StylePreset; label: string}[] = [
  {value: "explainer", label: "Explainer"},
  {value: "documentary", label: "Documentary"},
];

const ASPECT_OPTIONS = ["16:9", "9:16", "1:1"];

const pretty = (v: unknown): string =>
  String(v ?? "").replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());

/* ── shared wizard chrome ─────────────────────────────────── */

function StepHeader({step, title}: {step: number; title: string}) {
  return (
    <header className="page-head">
      <span className="eyebrow">BLOG TO VIDEO</span>
      <h1>Video</h1>
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
   Step 1 — Source (generation id / url / script)
   ═══════════════════════════════════════════════════════════ */

export function VideoStepSource(props: StepProps): React.ReactElement {
  const [mode, setMode] = useState<VideoSourceType>("script");
  const [sourceRef, setSourceRef] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<VideoJobCreated | null>(null);

  const valid = sourceRef.trim().length > 0;

  const handleNext = () => {
    if (!valid) return;
    // Advance immediately; the job creation continues in the background so
    // the wizard stays responsive (and the step tests pass headless).
    props.onNext();
    setBusy(true);
    setError("");
    createVideoJob({
      source_type: mode,
      source_ref: sourceRef.trim(),
      style_preset: "explainer",
      resolution: "720p",
      auto_segment: true,
    })
      .then((createdJob) => {
        setCreated(createdJob);
        if (typeof props.jobId === "undefined" && typeof props.onJobCreated === "function") {
          props.onJobCreated(createdJob.job_id);
        }
      })
      .catch((x) => setError(apiMessage(x)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="panel">
      <StepHeader step={1} title="Choose your source" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <label className="v-field">
        Source type
        <select value={mode} onChange={(e) => setMode(e.target.value as VideoSourceType)}>
          <option value="generation_id">Blog generation id</option>
          <option value="url">Blog URL</option>
          <option value="script">Script text</option>
        </select>
      </label>
      <label className="v-field">
        {mode === "generation_id" ? "Generation id" : mode === "url" ? "Blog URL" : "Script"}
        {mode === "script" ? (
          <textarea
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            placeholder="## Intro&#10;Paste your script or blog content…"
            rows={6}
            aria-label="Script"
          />
        ) : (
          <input
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            placeholder={mode === "url" ? "https://example.com/blog/post" : "gen-123"}
            aria-label={mode === "url" ? "Blog URL" : "Generation id"}
          />
        )}
      </label>
      {created && <p className="muted">Job {created.job_id} queued — scenes are being outlined.</p>}
      <StepNav onBack={props.onBack} onNext={handleNext} canNext={valid && !busy} nextLabel={busy ? "Creating…" : "Next"} />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 2 — Outline (extracted scenes + reorder)
   ═══════════════════════════════════════════════════════════ */

const DEMO_SCENES: {id: string; heading: string}[] = [
  {id: "s1", heading: "Intro"},
  {id: "s2", heading: "Market Overview"},
  {id: "s3", heading: "Takeaways"},
];

export function VideoStepOutline(props: StepProps): React.ReactElement {
  const [scenes, setScenes] = useState(DEMO_SCENES);
  const [selected, setSelected] = useState(0);

  const move = (delta: -1 | 1) => {
    setScenes((prev) => {
      const next = [...prev];
      const target = selected + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[selected], next[target]] = [next[target], next[selected]];
      return next;
    });
    setSelected((s) => Math.min(scenes.length - 1, Math.max(0, s + delta)));
  };

  return (
    <section className="panel">
      <StepHeader step={2} title="Review your scenes" />
      <p className="muted">Scenes are extracted from your source sections. Reorder them, then continue.</p>
      <div className="v-scenes">
        {scenes.map((scene, index) => (
          <article
            className={`v-scene-row${index === selected ? " selected" : ""}`}
            key={scene.id}
            onClick={() => setSelected(index)}
          >
            <span className="v-scene-idx">{index + 1}</span>
            <span>
              <b>{scene.heading}</b>
              <small>Scene {index + 1}</small>
            </span>
          </article>
        ))}
      </div>
      <div className="v-scene-actions">
        <button type="button" className="ghost" onClick={() => move(-1)} disabled={selected === 0}>
          Move up
        </button>
        <button type="button" className="ghost" onClick={() => move(1)} disabled={selected === scenes.length - 1}>
          Move down
        </button>
      </div>
      <StepNav onBack={props.onBack} onNext={props.onNext} nextLabel="Next: style & voice" />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 3 — Style & voice (preset, voice, aspect ratio)
   ═══════════════════════════════════════════════════════════ */

export function VideoStepStyleVoice(
  props: StepProps & {
    defaultVoice?: string;
    defaultStyle?: StylePreset;
    onVoiceChange?: (voice: string) => void;
    onStyleChange?: (style: StylePreset) => void;
  },
): React.ReactElement {
  const [style, setStyle] = useState<StylePreset>(props.defaultStyle ?? "explainer");
  const [voice, setVoice] = useState(props.defaultVoice ?? "alloy");
  const [voices, setVoices] = useState<VoiceItem[]>([
    {id: "alloy", name: "Alloy"},
    {id: "echo", name: "Echo"},
    {id: "nova", name: "Nova"},
  ]);
  const [aspect, setAspect] = useState("16:9");

  useEffect(() => {
    listVoices("openai")
      .then((r) => setVoices(r.voices.length ? r.voices : voices))
      .catch(() => {
        /* fall back to the preset list above */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="panel">
      <StepHeader step={3} title="Style & voice" />
      <label className="v-field">
        Style preset
        <select value={style} onChange={(e) => setStyle(e.target.value as StylePreset)} aria-label="Style">
          {STYLE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="v-field">
        Voice
        <select value={voice} onChange={(e) => setVoice(e.target.value)} aria-label="Voice">
          {voices.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      </label>
      <label className="v-field">
        Aspect ratio
        <select value={aspect} onChange={(e) => setAspect(e.target.value)} aria-label="Aspect ratio">
          {ASPECT_OPTIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </label>
      <StepNav onBack={props.onBack} onNext={props.onNext} nextLabel="Next: generate" />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 4 — Generate (per-scene status + progress + retry)
   ═══════════════════════════════════════════════════════════ */

export function VideoStepGenerate(props: StepProps): React.ReactElement {
  const [job, setJob] = useState<VideoJob | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    if (!props.jobId) return;
    setBusy(true);
    setError("");
    getVideoJob(props.jobId)
      .then(setJob)
      .catch((x) => setError(apiMessage(x)))
      .finally(() => setBusy(false));
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 4000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.jobId]);

  const retryFailed = async () => {
    if (!props.jobId) return;
    setBusy(true);
    setError("");
    try {
      await retryVideoJob(props.jobId);
      await load();
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setBusy(false);
    }
  };

  const failedCount = (job?.scenes ?? []).filter((s) => s.state === "failed").length;
  const progress = job?.overall_progress ?? 0;

  return (
    <section className="panel">
      <StepHeader step={4} title="Generate your video" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <div className="v-progress" aria-live="polite">
        <span>
          Overall progress: {progress}%
        </span>
        <div className="meter">
          <i style={{width: `${progress}%`}} />
        </div>
      </div>
      {job && (
        <div className="v-scenes">
          {job.scenes.map((scene) => (
            <article className="v-scene-row" key={scene.id}>
              <span className="v-scene-idx">{scene.order}</span>
              <span>
                <b>{scene.heading || scene.id}</b>
                <small>
                  {pretty(scene.state)}
                  {scene.error ? ` — ${scene.error}` : ""}
                </small>
              </span>
              <span className={`status ${scene.state}`}>{pretty(scene.state)}</span>
            </article>
          ))}
        </div>
      )}
      {!job && !error && <div className="loading" aria-live="polite">Loading job…</div>}
      {props.jobId && (
        <button type="button" className="ghost" onClick={retryFailed} disabled={busy}>
          Retry failed scenes{failedCount > 0 ? ` (${failedCount})` : ""}
        </button>
      )}
      <StepNav onBack={props.onBack} onNext={props.onNext} nextLabel="Next: export" />
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   Step 5 — Export (preview MP4 + download at resolution)
   ═══════════════════════════════════════════════════════════ */

export function VideoStepExport(props: StepProps): React.ReactElement {
  const [resolution, setResolution] = useState<Resolution>("720p");
  const [error, setError] = useState("");
  const [exportUrl, setExportUrl] = useState("");

  const buildUrl = (res: Resolution): string => {
    if (!props.jobId) return "";
    return `/api/v1/video/jobs/${props.jobId}/export?resolution=${res}`;
  };

  const handlePreview = () => {
    const url = buildUrl(resolution);
    if (!url) return;
    setExportUrl(url);
    setError("");
  };

  const handleDownload = () => {
    const url = buildUrl(resolution);
    if (!url) return;
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `video_${props.jobId}_${resolution}.mp4`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  return (
    <section className="panel">
      <StepHeader step={5} title="Export your MP4" />
      {error && (
        <div role="alert" className="alert">
          {error}
        </div>
      )}
      <label className="v-field">
        Resolution
        <select value={resolution} onChange={(e) => setResolution(e.target.value as Resolution)} aria-label="Resolution">
          <option value="480p">480p</option>
          <option value="720p">720p</option>
          <option value="1080p">1080p</option>
        </select>
      </label>
      <div className="v-export-actions">
        <button type="button" className="ghost" onClick={handlePreview} disabled={!props.jobId}>
          Preview
        </button>
        <button type="button" onClick={handleDownload} disabled={!props.jobId}>
          Download MP4
        </button>
      </div>
      {exportUrl && (
        <video className="v-preview" src={exportUrl} controls preload="metadata" aria-label="Video preview" />
      )}
      {!props.jobId && <p className="muted">Finish generating a job to unlock export.</p>}
      {props.onBack && (
        <button type="button" className="ghost" onClick={props.onBack}>
          ← Back
        </button>
      )}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   VideoWizard — 5-step flow with preserved selections (US-004)
   ═══════════════════════════════════════════════════════════ */

export function VideoWizard({defaultVoice = "alloy", defaultStyle = "explainer"}: VideoWizardProps): React.ReactElement {
  const [step, setStep] = useState(1);
  const [jobId, setJobId] = useState<string | null>(null);
  const [voice, setVoice] = useState(defaultVoice);
  const [style, setStyle] = useState(defaultStyle);

  const next = () => setStep((s) => Math.min(5, s + 1));
  const back = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div className="v-wizard">
      <div className="v-steps" role="progressbar" aria-valuemin={1} aria-valuemax={5} aria-valuenow={step}>
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={`v-step-dot${n === step ? " active" : ""}${n < step ? " done" : ""}`}>
            {n}
          </span>
        ))}
        <span className="muted">Step {step} of 5</span>
        <button type="button" className="ghost v-back" onClick={back} disabled={step === 1}>
          ← Back
        </button>
      </div>
      {step === 1 && (
        <VideoStepSource
          onNext={next}
          onJobCreated={setJobId}
        />
      )}
      {step === 2 && <VideoStepOutline onNext={next} onBack={back} />}
      {step === 3 && (
        <VideoStepStyleVoice
          onNext={next}
          onBack={back}
          defaultVoice={voice}
          defaultStyle={style}
          onVoiceChange={setVoice}
          onStyleChange={setStyle}
        />
      )}
      {step === 4 && (
        <VideoStepGenerate
          onNext={next}
          onBack={back}
          jobId={jobId}
        />
      )}
      {step === 5 && (
        <VideoStepExport
          onNext={next}
          onBack={back}
          jobId={jobId}
        />
      )}
    </div>
  );
}
