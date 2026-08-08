// ── Video — 5-step blog-to-video wizard ─────────────────────
//   P0-7 (US-001/US-004) + P1-5 (US-003 retry UX).
//
//   Pre-dev stub (t_ba5cfcec): the 5 step components are wired
//   with real prop contracts + types; each throws on render
//   ("not implemented — RED phase"). The developer replaces the
//   stubs with the real wizard in frontend/src/video.tsx.
//
//   API contract (src/routers/video.py, canonical /api/v1/video):
//     POST /api/v1/video/jobs            {source_type, source_ref, ...}
//     GET  /api/v1/video/jobs/{id}       job + scenes[] + overall_progress
//     POST /api/v1/video/jobs/{id}/retry {retried: [scene_id]}
//     GET  /api/v1/video/jobs/{id}/export?resolution=720p&partial=true
//     GET  /api/v1/video/voices?provider=openai

import React from "react";

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
};

/* ── stub components (throw on render — RED phase) ────────── */

export function VideoStepSource(_props: StepProps): React.ReactElement {
  throw new Error("VideoStepSource not implemented — RED phase");
}

export function VideoStepOutline(_props: StepProps): React.ReactElement {
  throw new Error("VideoStepOutline not implemented — RED phase");
}

export function VideoStepStyleVoice(_props: StepProps): React.ReactElement {
  throw new Error("VideoStepStyleVoice not implemented — RED phase");
}

export function VideoStepGenerate(_props: StepProps): React.ReactElement {
  throw new Error("VideoStepGenerate not implemented — RED phase");
}

export function VideoStepExport(_props: StepProps): React.ReactElement {
  throw new Error("VideoStepExport not implemented — RED phase");
}

export function VideoWizard(_props: VideoWizardProps): React.ReactElement {
  throw new Error("VideoWizard not implemented — RED phase");
}
