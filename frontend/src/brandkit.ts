/* ── Brand Kit pre-dev stubs ────────────────────────────────
 *  Types are real; components throw on render (RED phase).
 *  Developer replaces stubs with real implementations.
 * ──────────────────────────────────────────────────────────── */

import React from "react";

/* ── types ─────────────────────────────────────────────────── */

export type ColorPalette = {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
};

export type FontSet = {
  heading: string;
  body: string;
  accent: string;
};

export type LogoSet = {
  primary?: string | null;
  secondary?: string | null;
  icon?: string | null;
  watermark?: string | null;
};

export type BrandKit = {
  id: string;
  name: string;
  description: string;
  brand_type: string;
  colors: ColorPalette;
  fonts: FontSet;
  logos: LogoSet;
  version: number;
  created_at: string;
  updated_at: string;
};

export type BrandKitListResponse = {
  items: BrandKit[];
  total: number;
  limit: number;
  offset: number;
};

/* ── stub components (throw on render — RED phase) ─────────── */

export function BrandKitList(_props: {
  onSelect: (kit: BrandKit) => void;
}): React.ReactElement {
  throw new Error("BrandKitList not implemented — RED phase");
}

export function BrandKitDashboard(_props: {
  brandKitId: string;
  onBack: () => void;
}): React.ReactElement {
  throw new Error("BrandKitDashboard not implemented — RED phase");
}

export function BrandGuidelinesView(_props: {
  brandKitId: string;
  onBack: () => void;
}): React.ReactElement {
  throw new Error("BrandGuidelinesView not implemented — RED phase");
}
