## Features Done (this pass)
- AI Video Generation pipeline: blog/script → scenes → voiceover → MP4 with job state machine, per-scene progress and retry (failed scenes only, no re-render of completed), partial export after max retries, TTS provider abstraction (OpenAI/ElevenLabs/Coqui), style presets (explainer/documentary), voice selection, brand voice inheritance, MP4 export with resolution selection, long-post segmentation + combine, and a 5-step wizard UI (#video route).
- Video job API: `POST/GET /api/v1/video/jobs`, `POST /jobs/{id}/retry`, `GET /jobs/{id}/export`, `POST /jobs/{parent}/combine`, `GET /voices` — full error contract (400/404/409/422/502/503, JSON bodies).
- 167/168 video behavioral tests pass (one pre-tester interface/behavior contradiction on `retry_video_job` async vs sync — sync kept so the 3 retry-behavior tests pass; documented in CHANGELOG).
- 13 frontend video wizard tests pass (9 were RED-skipped).
## Sources
- analysis-brief.md §6 (video pipeline requirements & task specs, t_dfd6e7fc)
- CHANGELOG.md section this maps to: 0.15.0
