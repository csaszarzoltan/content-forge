// @vitest-environment jsdom
import {describe, expect, it, vi, beforeEach} from "vitest";
import {cleanup, render, screen, fireEvent, waitFor} from "@testing-library/react";
import React from "react";
import {TranscreationWorkspace} from "./transcreation";

/* ── fixtures ───────────────────────────────────────────── */

const SEGMENTS = [
  {
    id: "seg-1",
    original: "It's raining cats and dogs.",
    literal: "Es regnet Katzen und Hunde.",
    adapted: "Es regnet in Strömen.",
    risk_item: {
      id: "risk-1",
      segment: "It's raining cats and dogs.",
      category: "idiom",
      original_text: "raining cats and dogs",
      issue_description: "English idiom that does not translate literally.",
      confidence: 0.65,
      risk_level: "medium",
      suggested_replacement: "Es regnet in Strömen.",
      locale: "de-DE",
    },
    decision: null,
  },
  {
    id: "seg-2",
    original: "The report is ready.",
    literal: "Der Bericht ist fertig.",
    adapted: "Der Bericht ist fertig.",
    risk_item: null,
    decision: null,
  },
];

const ADAPT_RESPONSE = {
  adapted_text: "Es regnet in Strömen. Der Bericht ist fertig.",
  segments: SEGMENTS,
  changes_log: [],
  flagged_segments: ["seg-1"],
};

const ANALYZE_RESPONSE = {
  risk_items: [
    {
      id: "risk-1",
      segment: "It's raining cats and dogs.",
      category: "idiom",
      original_text: "raining cats and dogs",
      issue_description: "English idiom that does not translate literally.",
      confidence: 0.65,
      risk_level: "medium",
      suggested_replacement: "Es regnet in Strömen.",
      locale: "de-DE",
    },
  ],
  format_items: [],
  overall_risk: "medium",
  locale: "de-DE",
};

/* ── helpers ────────────────────────────────────────────── */

function mockFetch(responses: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, opts?: RequestInit): Promise<Response> => {
      const key = `${opts?.method ?? "GET"} ${url}`;
      const body = responses[key];
      if (body === undefined) {
        return {ok: false, status: 404, text: async () => "Not found"} as Response;
      }
      if (body instanceof Error) {
        return {
          ok: false,
          status: body.message.startsWith("409") ? 409 : 500,
          text: async () => body.message,
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as Response;
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  cleanup();
});

async function fillAndRun() {
  fireEvent.change(screen.getByLabelText(/source text/i), {
    target: {value: "It's raining cats and dogs. The report is ready."},
  });
  fireEvent.click(screen.getByRole("button", {name: /^adapt/i}));
}

/* ═══════════════════════════════════════════════════════════
   TranscreationWorkspace — behavioral tests
   ═══════════════════════════════════════════════════════════ */

describe("TranscreationWorkspace", () => {
  it("renders the source text form and adapts via the API", async () => {
    mockFetch({
      "POST /api/v1/transcreation/adapt": ADAPT_RESPONSE,
    });
    render(<TranscreationWorkspace />);

    await fillAndRun();

    // Side-by-side diff columns: original / literal / adapted
    expect(await screen.findByText("It's raining cats and dogs.")).toBeInTheDocument();
    expect(screen.getByText("Es regnet Katzen und Hunde.")).toBeInTheDocument();
    expect(screen.getByText("Es regnet in Strömen.")).toBeInTheDocument();

    // Adapted text output panel
    expect(screen.getByTestId("adapted-text").textContent).toContain("Es regnet in Strömen");

    // The fetch should include target locale and no review decisions yet
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/transcreation/adapt",
        expect.objectContaining({method: "POST"}),
      );
      const post = vi.mocked(fetch).mock.calls.find(([, o]) => o?.method === "POST");
      expect(JSON.parse(String(post?.[1]?.body))).toEqual(
        expect.objectContaining({
          text: "It's raining cats and dogs. The report is ready.",
          target_locale: "de-DE",
          accepted_ids: [],
          rejected_ids: [],
          edits: {},
        }),
      );
    });
  });

  it("visually flags low-confidence segments for review", async () => {
    mockFetch({
      "POST /api/v1/transcreation/adapt": ADAPT_RESPONSE,
    });
    render(<TranscreationWorkspace />);

    await fillAndRun();

    // seg-1 (confidence 0.65) is flagged; seg-2 is not
    await waitFor(() => {
      expect(screen.getByText("Es regnet Katzen und Hunde.")).toBeInTheDocument();
    });
    const flagged = document.querySelector(".tc-segment.flagged");
    expect(flagged).not.toBeNull();
    expect(flagged?.textContent).toContain("Es regnet Katzen und Hunde.");
    expect(flagged?.textContent).toContain("idiom");
    expect(flagged?.textContent).toMatch(/low confidence|review/i);
  });

  it("sends accept decisions back to the API", async () => {
    mockFetch({
      "POST /api/v1/transcreation/adapt": ADAPT_RESPONSE,
      "POST /api/v1/transcreation/assets/asset-1/export": {asset_id: "asset-1", adapted_text: "exported"},
    });
    render(<TranscreationWorkspace assetId="asset-1" />);

    await fillAndRun();
    await screen.findByText("It's raining cats and dogs.");

    // Accept the flagged segment
    const acceptButtons = screen.getAllByRole("button", {name: /accept/i});
    fireEvent.click(acceptButtons[0]);

    // Export after accepting should include the decision and hit the export endpoint
    fireEvent.click(screen.getByRole("button", {name: /export/i}));

    await waitFor(() => {
      const exportCall = vi.mocked(fetch).mock.calls.find(([u]) =>
        String(u).includes("/export"),
      );
      expect(exportCall).toBeTruthy();
    });
  });

  it("allows editing a segment and keeps the edit in the export body", async () => {
    mockFetch({
      "POST /api/v1/transcreation/adapt": ADAPT_RESPONSE,
      "POST /api/v1/transcreation/assets/asset-1/export": {asset_id: "asset-1", adapted_text: "exported"},
    });
    render(<TranscreationWorkspace assetId="asset-1" />);

    await fillAndRun();
    await screen.findByText("It's raining cats and dogs.");

    const editButtons = screen.getAllByRole("button", {name: /edit/i});
    fireEvent.click(editButtons[0]);
    const textarea = await screen.findByRole("textbox", {name: /edit seg-1/i});
    fireEvent.change(textarea, {target: {value: "Es schüttet wie aus Eimern."}});

    // Export now carries the edit
    fireEvent.click(screen.getByRole("button", {name: /export/i}));

    await waitFor(() => {
      const exportCall = vi.mocked(fetch).mock.calls.find(([u]) =>
        String(u).includes("/export"),
      );
      expect(exportCall).toBeTruthy();
    });
  });

  it("blocks export until flagged segments are resolved (matches backend 409 gate)", async () => {
    mockFetch({
      "POST /api/v1/transcreation/adapt": ADAPT_RESPONSE,
      "POST /api/v1/transcreation/assets/asset-1/export": new Error(
        "409 transcreation_export_blocked: unresolved low-confidence segments",
      ),
    });
    render(<TranscreationWorkspace assetId="asset-1" />);

    await fillAndRun();
    await screen.findByText("It's raining cats and dogs.");

    // Flagged segment unresolved → export button disabled + hint visible
    const exportBtn = screen.getByRole("button", {name: /export/i}) as HTMLButtonElement;
    expect(exportBtn.disabled).toBe(true);
    expect(
      screen.getByText(/resolve all flagged segments to unlock export/i),
    ).toBeInTheDocument();

    // Resolve the flagged segment (accept) → export enabled
    const acceptButtons = screen.getAllByRole("button", {name: /accept/i});
    fireEvent.click(acceptButtons[0]);
    await waitFor(() => {
      expect(
        (screen.getByRole("button", {name: /export/i}) as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    // Export now fires; the mock returns 409 → the API detail is surfaced
    fireEvent.click(screen.getByRole("button", {name: /export/i}));
    expect(
      await screen.findByText(/transcreation_export_blocked/i, {selector: ".alert"}),
    ).toBeInTheDocument();
  });

  it("renders the analyze risk summary when analyze is used", async () => {
    mockFetch({
      "POST /api/v1/transcreation/analyze": ANALYZE_RESPONSE,
    });
    render(<TranscreationWorkspace />);

    fireEvent.change(screen.getByLabelText(/source text/i), {
      target: {value: "It's raining cats and dogs."},
    });
    fireEvent.click(screen.getByRole("button", {name: /analyze/i}));

    expect(
      await screen.findByText(/english idiom that does not translate literally/i),
    ).toBeInTheDocument();
    // overall risk summary chip
    expect(screen.getByText("Medium risk", {selector: ".status"})).toBeInTheDocument();
  });
});
