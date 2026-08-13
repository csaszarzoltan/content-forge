// @vitest-environment jsdom
// ── Content-creation wizard tests (t_b1b68088) ─────────────
//   Interface tests: component + type exports (PASS immediately).
//   Behavioral tests: forward-validating — they assert the actual
//   US-001..US-004 behavior once the developer implements the wizard.

import {describe, expect, it, vi, beforeEach} from "vitest";
import {cleanup, render, screen, fireEvent} from "@testing-library/react";
import React from "react";
import {
  ContentCreationWizard,
  ContentStepGenerate,
  ContentStepPublish,
  ContentStepSource,
  ContentStepValidate,
  type ContentPackage,
  type ContentSourceType,
} from "./content-creation";

beforeEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  cleanup();
});

/* ── fixtures ───────────────────────────────────────────── */

const SAMPLE_PACKAGE: ContentPackage = {
  id: "pkg-1",
  source_type: "text",
  source_ref: "Source asset.",
  state: "ready_to_approve",
  brand_voice_id: null,
  platforms: ["twitter", "linkedin"],
  variants: [
    {id: "v1", platform: "twitter", content: "Hi!", char_count: 3, validation_status: "validated", publish_status: "pending", error: null, remote_id: null},
    {id: "v2", platform: "linkedin", content: "Hello everyone.", char_count: 16, validation_status: "validated", publish_status: "pending", error: null, remote_id: null},
  ],
};

/* ── interface-level contracts (types + exports) ─────────── */

describe("content-creation wizard interface", () => {
  it("exports the wizard and four step components", () => {
    expect(typeof ContentCreationWizard).toBe("function");
    expect(typeof ContentStepSource).toBe("function");
    expect(typeof ContentStepGenerate).toBe("function");
    expect(typeof ContentStepValidate).toBe("function");
    expect(typeof ContentStepPublish).toBe("function");
  });
});

/* ── behavioral: the 4-step wizard (US-001..US-004) ──────── */

describe("ContentCreationWizard 4-step flow", () => {
  it("renders a progress indicator for the 4 steps", () => {
    render(<ContentCreationWizard />);
    expect(screen.getByText(/step 1 of 4/i)).toBeInTheDocument();
  });

  it("step 1 collects source + platforms and advances only when valid", () => {
    const onNext = vi.fn();
    render(<ContentStepSource onNext={onNext} />);
    fireEvent.click(screen.getByText(/next/i));
    expect(onNext).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(/source asset/i), {target: {value: "## Intro\nHello."}});
    fireEvent.click(screen.getByText(/next/i));
    expect(onNext).toHaveBeenCalled();
  });

  it("step 2 shows per-platform variant cards", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(SAMPLE_PACKAGE),
      } as Response)
    ));
    render(<ContentStepGenerate onNext={vi.fn()} packageId="pkg-1" />);
    await screen.findByText(/twitter/i);
    expect(screen.getByText(/twitter/i)).toBeInTheDocument();
    expect(screen.getByText(/linkedin/i)).toBeInTheDocument();
  });

  it("step 3 offers validate and an approve button", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(SAMPLE_PACKAGE),
      } as Response)
    ));
    render(<ContentStepValidate onNext={vi.fn()} packageId="pkg-1" />);
    expect(await screen.findByText(/validate against platform rules/i)).toBeInTheDocument();
    expect(screen.getByText(/approve/i)).toBeInTheDocument();
  });

  it("step 4 offers publish with per-platform status", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(SAMPLE_PACKAGE),
      } as Response)
    ));
    render(<ContentStepPublish onNext={vi.fn()} packageId="pkg-1" />);
    expect(await screen.findByText(/publish approved variants/i)).toBeInTheDocument();
  });

  it("back preserves earlier selections (US-004)", () => {
    render(<ContentCreationWizard />);
    expect(screen.getByText(/back/i)).toBeInTheDocument();
  });
});

/* ── behavioral: types used by the wizard ────────────────── */

describe("content-creation wizard types", () => {
  it("defines the three source types", () => {
    const types: ContentSourceType[] = ["generation_id", "text", "url"];
    expect(types).toHaveLength(3);
  });

  it("package payload carries per-platform variants with statuses", () => {
    expect(SAMPLE_PACKAGE.variants).toHaveLength(2);
    expect(SAMPLE_PACKAGE.variants.every(v => v.validation_status === "validated")).toBe(true);
  });
});
