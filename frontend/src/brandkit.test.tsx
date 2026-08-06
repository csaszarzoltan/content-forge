// @vitest-environment jsdom
import {describe, expect, it, vi, beforeEach} from "vitest";
import {render, screen, fireEvent, waitFor} from "@testing-library/react";
import React from "react";
import {
  BrandKitList,
  BrandKitDashboard,
  BrandGuidelinesView,
  type BrandKit,
  type ColorPalette,
} from "./brandkit";

/* ── fixtures ───────────────────────────────────────────── */

const PALETTE: ColorPalette = {
  primary: "#1a2b3c",
  secondary: "#4d5e6f",
  accent: "#ff6600",
  background: "#ffffff",
  text: "#222222",
};

const SAMPLE_KIT: BrandKit = {
  id: "bk-001",
  name: "Acme Brand",
  description: "The Acme corporate identity",
  brand_type: "corporate",
  colors: PALETTE,
  fonts: {heading: "Inter", body: "DM Sans", accent: "Fira Code"},
  logos: {},
  version: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const SECOND_KIT: BrandKit = {
  ...SAMPLE_KIT,
  id: "bk-002",
  name: "Startup Brand",
  description: "Playful startup identity",
  brand_type: "startup",
  colors: {...PALETTE, primary: "#00cc88"},
};

/* ── helpers ────────────────────────────────────────────── */

function mockFetch(responses: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, opts?: RequestInit) => {
      const key = `${opts?.method ?? "GET"} ${url}`;
      const body = responses[key];
      if (body === undefined) {
        return {ok: false, status: 404, text: async () => "Not found"};
      }
      return {
        ok: true,
        status: 200,
        json: async () => body,
        text: async () => JSON.stringify(body),
      };
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/* ═══════════════════════════════════════════════════════════
   Brand Kit List — behavioral tests
   ═══════════════════════════════════════════════════════════ */

describe("BrandKitList", () => {
  it("renders each brand kit as a card with name and color swatches", async () => {
    mockFetch({
      "GET /api/v1/brand-kit": {
        items: [SAMPLE_KIT, SECOND_KIT],
        total: 2,
        limit: 20,
        offset: 0,
      },
    });

    render(<BrandKitList onSelect={vi.fn()} />);

    expect(await screen.findByText("Acme Brand")).toBeInTheDocument();
    expect(screen.getByText("Startup Brand")).toBeInTheDocument();

    // Each card should show color swatches
    const swatches = screen.getAllByTestId(/^swatch-/);
    expect(swatches.length).toBeGreaterThanOrEqual(10); // 5 per kit × 2 kits
  });

  it("shows an onboarding empty state when no brand kits exist", async () => {
    mockFetch({
      "GET /api/v1/brand-kit": {items: [], total: 0, limit: 20, offset: 0},
    });

    render(<BrandKitList onSelect={vi.fn()} />);

    expect(
      await screen.findByText(/create your first brand kit/i),
    ).toBeInTheDocument();
  });

  it("posts to /api/v1/brand-kit with the correct JSON body on create", async () => {
    const createdKit = {
      ...SAMPLE_KIT,
      id: "bk-new",
      name: "New Brand",
    };
    mockFetch({
      "GET /api/v1/brand-kit": {items: [], total: 0, limit: 20, offset: 0},
      "POST /api/v1/brand-kit": createdKit,
    });

    render(<BrandKitList onSelect={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: {value: "New Brand"},
    });
    fireEvent.change(screen.getByLabelText(/description/i), {
      target: {value: "A fresh brand"},
    });
    fireEvent.click(screen.getByRole("button", {name: /create/i}));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/brand-kit",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(
            expect.objectContaining({
              name: "New Brand",
              description: "A fresh brand",
            }),
          ),
        }),
      );
    });
  });

  it("shows a success confirmation after creating a brand kit", async () => {
    mockFetch({
      "GET /api/v1/brand-kit": {items: [], total: 0, limit: 20, offset: 0},
      "POST /api/v1/brand-kit": SAMPLE_KIT,
    });

    render(<BrandKitList onSelect={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: {value: "Acme Brand"},
    });
    fireEvent.click(screen.getByRole("button", {name: /create/i}));

    expect(await screen.findByText(/created|success|brand kit/i)).toBeInTheDocument();
  });

  it("shows a friendly error message on create failure", async () => {
    mockFetch({
      "GET /api/v1/brand-kit": {items: [], total: 0, limit: 20, offset: 0},
      "POST /api/v1/brand-kit": undefined, // 404
    });

    render(<BrandKitList onSelect={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: {value: "Broken Brand"},
    });
    fireEvent.click(screen.getByRole("button", {name: /create/i}));

    expect(
      await screen.findByText(/kept your work|check the api/i),
    ).toBeInTheDocument();
  });
});

/* ═══════════════════════════════════════════════════════════
   Brand Kit Dashboard — behavioral tests
   ═══════════════════════════════════════════════════════════ */

describe("BrandKitDashboard", () => {
  it("shows 5 color swatches with hex inputs for primary, secondary, accent, background, text", async () => {
    mockFetch({
      "GET /api/v1/brand-kit/bk-001": SAMPLE_KIT,
    });

    render(<BrandKitDashboard brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByText("Acme Brand");

    const slots = ["primary", "secondary", "accent", "background", "text"] as const;
    for (const slot of slots) {
      expect(screen.getByTestId(`hex-${slot}`)).toBeInTheDocument();
      expect(screen.getByTestId(`hex-${slot}`)).toHaveValue(PALETTE[slot]);
    }
  });

  it("updates the live preview CSS variables when a hex input is edited", async () => {
    mockFetch({
      "GET /api/v1/brand-kit/bk-001": SAMPLE_KIT,
    });

    render(<BrandKitDashboard brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByText("Acme Brand");

    const primaryInput = screen.getByTestId("hex-primary");
    fireEvent.change(primaryInput, {target: {value: "#00ff00"}});

    const preview = screen.getByTestId("brandkit-preview");
    expect(preview.style.getPropertyValue("--brand-primary")).toBe("#00ff00");
  });

  it("has 3 font slots (heading, body, accent) that update the preview font-family", async () => {
    mockFetch({
      "GET /api/v1/brand-kit/bk-001": SAMPLE_KIT,
    });

    render(<BrandKitDashboard brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByText("Acme Brand");

    const headingInput = screen.getByTestId("font-heading");
    const bodyInput = screen.getByTestId("font-body");
    const accentInput = screen.getByTestId("font-accent");

    expect(headingInput).toHaveValue("Inter");
    expect(bodyInput).toHaveValue("DM Sans");
    expect(accentInput).toHaveValue("Fira Code");

    fireEvent.change(headingInput, {target: {value: "Manrope"}});

    const preview = screen.getByTestId("brandkit-preview");
    expect(preview.style.getPropertyValue("--brand-font-heading")).toBe(
      "Manrope",
    );
  });

  it("has a logo upload zone that accepts drag-and-drop and calls the upload endpoint", async () => {
    mockFetch({
      "GET /api/v1/brand-kit/bk-001": SAMPLE_KIT,
      "POST /api/v1/brand-kit/upload": {
        path: "/uploads/logo.png",
        filename: "logo.png",
        size: 12345,
      },
    });

    render(<BrandKitDashboard brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByText("Acme Brand");

    const dropZone = screen.getByTestId("logo-drop-zone-primary");
    expect(dropZone).toBeInTheDocument();

    const file = new File(["<svg/>"], "logo.png", {type: "image/png"});

    fireEvent.drop(dropZone, {
      dataTransfer: {files: [file]},
    });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/brand-kit/upload",
        expect.objectContaining({method: "POST"}),
      );
    });
  });

  it("calls the update endpoint on save and shows success feedback", async () => {
    mockFetch({
      "GET /api/v1/brand-kit/bk-001": SAMPLE_KIT,
      "PUT /api/v1/brand-kit/bk-001": SAMPLE_KIT,
    });

    render(<BrandKitDashboard brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByText("Acme Brand");

    fireEvent.click(screen.getByRole("button", {name: /save/i}));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/brand-kit/bk-001",
        expect.objectContaining({method: "PUT"}),
      );
    });

    expect(
      await screen.findByText(/saved|success|updated/i),
    ).toBeInTheDocument();
  });
});

/* ═══════════════════════════════════════════════════════════
   Brand Guidelines View — behavioral tests
   ═══════════════════════════════════════════════════════════ */

describe("BrandGuidelinesView", () => {
  it("fetches guidelines HTML from the API and renders it", async () => {
    const html = "<h1>Acme Style Guide</h1><p>Use primary blue for CTAs.</p>";
    mockFetch({
      "GET /api/v1/brand-kit/guidelines?brand_kit_id=bk-001": html,
    });

    render(<BrandGuidelinesView brandKitId="bk-001" onBack={vi.fn()} />);

    const container = await screen.findByTestId("guidelines-container");
    expect(container.innerHTML).toContain("Acme Style Guide");
  });

  it("provides a download button that triggers HTML download", async () => {
    const html = "<h1>Brand Guide</h1>";
    mockFetch({
      "GET /api/v1/brand-kit/guidelines?brand_kit_id=bk-001": html,
    });

    render(<BrandGuidelinesView brandKitId="bk-001" onBack={vi.fn()} />);

    await screen.findByTestId("guidelines-container");

    const downloadBtn = screen.getByRole("button", {name: /download/i});
    expect(downloadBtn).toBeInTheDocument();

    // Clicking download should create a blob URL and trigger download
    const clickSpy = vi.spyOn(document.createElement("a"), "click");
    fireEvent.click(downloadBtn);
    expect(clickSpy).toHaveBeenCalled();
  });

  it("calls onBack when the back button is clicked", async () => {
    const html = "<h1>Guide</h1>";
    mockFetch({
      "GET /api/v1/brand-kit/guidelines?brand_kit_id=bk-001": html,
    });

    const onBack = vi.fn();
    render(<BrandGuidelinesView brandKitId="bk-001" onBack={onBack} />);

    await screen.findByTestId("guidelines-container");

    fireEvent.click(screen.getByRole("button", {name: /back|←/i}));
    expect(onBack).toHaveBeenCalled();
  });
});
