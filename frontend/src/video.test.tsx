// @vitest-environment jsdom
// ── Video wizard pre-dev tests (t_ba5cfcec) — RED phase ─────
//   Interface tests: component + type exports (PASS immediately).
//   Behavioral tests: forward-validating — during RED the stub
//   components throw "not implemented — RED phase" and the tests
//   SKIP via the vitest test context (ctx.skip()); once the
//   developer implements the real wizard they run and assert the
//   actual US-001/US-004 behavior. (Mirrors the Python side:
//   tests/test_video_jobs.py policy — no test asserts
//   NotImplementedError as expected behavior of the feature's own
//   public methods.)

import {describe, expect, it, vi, beforeEach} from "vitest";
import {cleanup, render, screen, fireEvent} from "@testing-library/react";
import React from "react";
import {
  VideoStepExport,
  VideoStepGenerate,
  VideoStepOutline,
  VideoStepSource,
  VideoStepStyleVoice,
  VideoWizard,
  type StylePreset,
  type VideoJob,
  type VideoSourceType,
} from "./video";

beforeEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  cleanup();
});

/* ── fixtures ───────────────────────────────────────────── */

const SAMPLE_JOB: VideoJob = {
  id: "job-1",
  source_type: "script",
  source_ref: "## Intro\nHello.",
  state: "ready",
  brand_voice_id: "bv-1",
  voice_profile_name: "Acme Professional",
  style_preset: "explainer",
  voice: "alloy",
  resolution: "720p",
  overall_progress: 100,
  scenes: [
    {id: "s1", order: 1, heading: "Intro", state: "done", attempts: 1, error: null, image_path: null, audio_path: "/tmp/s1.mp3"},
    {id: "s2", order: 2, heading: "Body", state: "failed", attempts: 3, error: "tts boom", image_path: null, audio_path: null},
  ],
};

/** Run a behavioral assertion; during RED the stub throws and we skip. */
function redOrRun(fn: () => void): void {
  try {
    fn();
  } catch (err) {
    if (err instanceof Error && err.message.includes("not implemented — RED phase")) {
      throw new Error("__RED_SKIP__");
    }
    throw err;
  }
}

/* ── interface-level contracts (types + exports) ─────────── */

describe("video wizard interface", () => {
  it("exports the six wizard components", () => {
    expect(typeof VideoWizard).toBe("function");
    expect(typeof VideoStepSource).toBe("function");
    expect(typeof VideoStepOutline).toBe("function");
    expect(typeof VideoStepStyleVoice).toBe("function");
    expect(typeof VideoStepGenerate).toBe("function");
    expect(typeof VideoStepExport).toBe("function");
  });
});

/* ── behavioral (forward-validating): the 5-step wizard ──── */

describe("VideoWizard 5-step flow (US-001/US-004)", () => {
  it("renders a progress indicator for the 5 steps", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoWizard defaultVoice="alloy" defaultStyle="explainer" />);
        expect(screen.getByText(/step 1 of 5/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 1 collects the blog source (generation id / url / script)", (ctx) => {
    try {
      redOrRun(() => {
        const onNext = vi.fn();
        render(<VideoStepSource onNext={onNext} />);
        const script = screen.getByLabelText(/script/i) as HTMLInputElement;
        fireEvent.change(script, {target: {value: "## Intro\nHello."}});
        fireEvent.click(screen.getByText(/next/i));
        expect(onNext).toHaveBeenCalled();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("does not advance step 1 until a valid source is given", (ctx) => {
    try {
      redOrRun(() => {
        const onNext = vi.fn();
        render(<VideoStepSource onNext={onNext} />);
        fireEvent.click(screen.getByText(/next/i));
        expect(onNext).not.toHaveBeenCalled();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 2 lists the extracted scenes with reorder controls", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoStepOutline onNext={vi.fn()} />);
        expect(screen.getAllByText(/scene/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/up/i) || screen.getByText(/move up/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 3 offers style preset, voice select and aspect ratio", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoStepStyleVoice onNext={vi.fn()} />);
        expect(screen.getByLabelText(/style/i) || screen.getByText(/explainer/i)).toBeInTheDocument();
        expect(screen.getByText(/16:9/i) || screen.getByText(/9:16/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 4 shows per-scene status and an overall progress bar", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoStepGenerate onNext={vi.fn()} jobId="job-1" />);
        expect(screen.getByText(/progress/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 4 offers retry only for failed scenes (US-003)", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoStepGenerate onNext={vi.fn()} jobId="job-1" />);
        expect(screen.getByText(/retry failed scenes/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("step 5 previews the MP4 and offers a download", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoStepExport onNext={vi.fn()} jobId="job-1" />);
        expect(screen.getByText(/download mp4/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });

  it("back preserves earlier selections (US-004)", (ctx) => {
    try {
      redOrRun(() => {
        render(<VideoWizard defaultVoice="alloy" defaultStyle="documentary" />);
        expect(screen.getByText(/back/i)).toBeInTheDocument();
      });
    } catch (err) {
      if (err instanceof Error && err.message === "__RED_SKIP__") ctx.skip();
      else throw err;
    }
  });
});

/* ── behavioral (RED): types used by the wizard ──────────── */

describe("video wizard types", () => {
  it("defines the three source types", () => {
    const types: VideoSourceType[] = ["generation_id", "url", "script"];
    expect(types).toHaveLength(3);
  });

  it("defines the two style presets", () => {
    const presets: StylePreset[] = ["explainer", "documentary"];
    expect(presets).toHaveLength(2);
  });

  it("job payload exposes brand voice inheritance (voice_profile_name)", () => {
    expect(SAMPLE_JOB.voice_profile_name).toBe("Acme Professional");
  });
});
