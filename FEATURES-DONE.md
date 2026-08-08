## Features Done (this pass)
- AI Video Generation pipeline: blog/script → scenes → voiceover → MP4 with job state machine, per-scene progress and retry (failed scenes only, no re-render of completed), partial export after max retries, **background worker (`VideoJobWorker`) that drives queued jobs end-to-end — TTS per scene → done, render → ready|failed (attempts ≤ 3)**, TTS provider abstraction (OpenAI/ElevenLabs/Coqui), style presets (explainer/documentary), voice selection, brand voice inheritance, MP4 export with resolution selection, long-post segmentation + combine (rendered clip concatenation), and a 5-step wizard UI (#video route).
- Video job API: `POST/GET /api/v1/video/jobs`, `POST /jobs/{id}/retry`, `GET /jobs/{id}/export`, `POST /jobs/{parent}/combine`, `GET /voices` — full error contract (400/404/409/422/502/503, JSON bodies).
- 185/186 video behavioral tests pass (one pre-tester interface/behavior contradiction on `retry_video_job` async vs sync — sync kept so the 3 retry-behavior tests pass; documented in CHANGELOG). Includes the BLOCKER-1 regression: real API create → real worker path → job reaches `ready` with a playable MP4 export (no store-seam scene manipulation).
- 13 frontend video wizard tests pass (9 were RED-skipped).
## Sources
- analysis-brief.md §6 (video pipeline requirements & task specs, t_dfd6e7fc)
- CHANGELOG.md section this maps to: 0.15.0
