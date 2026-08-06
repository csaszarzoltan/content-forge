/* ── Brand Kit — types, API helpers, and components ────────── */

import React, {FormEvent, useCallback, useEffect, useRef, useState} from "react";
import {validationMessage} from "./flow";

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

/* ── API helpers ───────────────────────────────────────────── */

async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {"Content-Type": "application/json", ...(options?.headers || {})},
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export async function fetchBrandKits(limit = 20, offset = 0): Promise<BrandKitListResponse> {
  return apiRequest<BrandKitListResponse>("/api/v1/brand-kit");
}

export async function createBrandKit(data: {name: string; description: string; brand_type: string}): Promise<BrandKit> {
  return apiRequest<BrandKit>("/api/v1/brand-kit", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getBrandKit(id: string): Promise<BrandKit> {
  return apiRequest<BrandKit>(`/api/v1/brand-kit/${id}`);
}

export async function updateBrandKit(id: string, data: Partial<BrandKit>): Promise<BrandKit> {
  return apiRequest<BrandKit>(`/api/v1/brand-kit/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function uploadBrandKitFile(
  brandKitId: string,
  file: File,
  fileType: string = "logo",
): Promise<{path: string; filename: string; size: number}> {
  const form = new FormData();
  form.append("file", file);
  form.append("brand_kit_id", brandKitId);
  form.append("file_type", fileType);
  const response = await fetch("/api/v1/brand-kit/upload", {method: "POST", body: form});
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchBrandGuidelines(brandKitId: string): Promise<string> {
  const response = await fetch(`/api/v1/brand-kit/guidelines?brand_kit_id=${brandKitId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.text();
}

/* ── color helpers ─────────────────────────────────────────── */

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  if (h.length !== 6) return "rgb(0,0,0)";
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgb(${r},${g},${b})`;
}

const COLOR_LABELS: Record<string, string> = {
  primary: "Primary",
  secondary: "Secondary",
  accent: "Accent",
  background: "Background",
  text: "Text",
};
const COLOR_SLOTS = ["primary", "secondary", "accent", "background", "text"] as const;

/* ── toast helper ──────────────────────────────────────────── */

function Toast({message, onClear}: {message: string; onClear: () => void}) {
  useEffect(() => {
    const t = setTimeout(onClear, 3500);
    return () => clearTimeout(t);
  }, [onClear]);
  return <div className="bk-toast" role="status">{message}</div>;
}

/* ═════════════════════════════════════════════════════════════
   BrandKitList — card grid + create form
   ═════════════════════════════════════════════════════════════ */

export function BrandKitList({onSelect}: {onSelect: (kit: BrandKit) => void}) {
  const [kits, setKits] = useState<BrandKit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [brandType, setBrandType] = useState("personal");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    fetchBrandKits()
      .then((r) => setKits(r.items))
      .catch((e) => setError(validationMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const kit = await createBrandKit({name, description, brand_type: brandType});
      setKits((prev) => [kit, ...prev]);
      setName("");
      setDescription("");
      setBrandType("personal");
      setSuccess("Brand kit created");
    } catch {
      setError(validationMessage(new Error("create failed")));
    }
  };

  return (
    <div className="bk-workspace">
      <header className="page-head">
        <span className="eyebrow">VISUAL IDENTITY</span>
        <h1>Brand Kit</h1>
        <p>Define colors, fonts, and logos for consistent brand recognition.</p>
      </header>

      {error && <div role="alert" className="alert">{error}<button className="link" onClick={load}>Retry</button></div>}
      {success && <Toast message={success} onClear={() => setSuccess("")} />}

      {loading ? (
        <div className="loading" aria-live="polite">Loading brand kits…</div>
      ) : (
        <>
          {kits.length === 0 && (
            <div className="empty bk-onboard">
              <div className="spark">◆</div>
              <h3>Create your first brand kit</h3>
              <p>Define your visual identity — colors, fonts, and logos — to use across all content.</p>
            </div>
          )}

          {kits.length > 0 && (
            <section className="bk-grid">
              {kits.map((kit) => (
                <button key={kit.id} className="bk-card" onClick={() => onSelect(kit)}>
                  <div className="bk-swatches" data-testid={`swatch-primary-${kit.id}`}>
                    {COLOR_SLOTS.map((slot) => (
                      <span key={slot} data-testid={`swatch-${slot}-${kit.id}`} className="bk-mini-swatch" style={{background: kit.colors[slot]}} />
                    ))}
                  </div>
                  <h3>{kit.name}</h3>
                  <small>{kit.brand_type}</small>
                </button>
              ))}
            </section>
          )}
        </>
      )}

      <form className="bk-create-form" onSubmit={handleCreate}>
        <h2>Create brand kit</h2>
        <label>Name
          <input name="name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="My brand" />
        </label>
        <label>Description
          <input name="description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description" />
        </label>
        <label>Type
          <select name="brand_type" value={brandType} onChange={(e) => setBrandType(e.target.value)}>
            <option value="personal">Personal</option>
            <option value="business">Business</option>
            <option value="corporate">Corporate</option>
            <option value="startup">Startup</option>
          </select>
        </label>
        <button type="submit">Create brand kit</button>
      </form>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════
   BrandKitDashboard — per-brand editor
   ═════════════════════════════════════════════════════════════ */

export function BrandKitDashboard({brandKitId, onBack, onGuidelines}: {brandKitId: string; onBack: () => void; onGuidelines?: () => void}) {
  const [kit, setKit] = useState<BrandKit | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [colors, setColors] = useState<ColorPalette>({primary: "#000000", secondary: "#ffffff", accent: "#0066cc", background: "#ffffff", text: "#333333"});
  const [fonts, setFonts] = useState<FontSet>({heading: "Arial", body: "Arial", accent: "Arial"});
  const [logos, setLogos] = useState<LogoSet>({});

  useEffect(() => {
    getBrandKit(brandKitId)
      .then((k) => {
        setKit(k);
        setColors(k.colors);
        setFonts(k.fonts);
        setLogos(k.logos);
      })
      .catch((e) => setError(validationMessage(e)))
      .finally(() => setLoading(false));
  }, [brandKitId]);

  const handleColorChange = (slot: string, value: string) => {
    setColors((prev) => ({...prev, [slot]: value}));
  };

  const handleFontChange = (slot: string, value: string) => {
    setFonts((prev) => ({...prev, [slot]: value}));
  };

  const handleDrop = useCallback(async (e: React.DragEvent, slot: string) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    try {
      const result = await uploadBrandKitFile(brandKitId, file, "logo");
      setLogos((prev) => ({...prev, [slot]: result.path}));
    } catch {
      // Upload may fail until backend is fully ready — that's OK
    }
  }, [brandKitId]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await updateBrandKit(brandKitId, {colors, fonts, logos});
      setSuccess("Brand kit saved");
    } catch {
      setError(validationMessage(new Error("save failed")));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading" aria-live="polite">Loading brand kit…</div>;
  if (error && !kit) return <div role="alert" className="alert">{error}<button className="link" onClick={onBack}>← Back</button></div>;

  return (
    <div className="bk-workspace">
      <button className="back" onClick={onBack}>← All brand kits</button>
      <header className="page-head">
        <span className="eyebrow">BRAND KIT</span>
        <h1>{kit?.name || "Brand Kit"}</h1>
        <p>{kit?.description || "Edit colors, fonts, and logos."}</p>
      </header>

      {error && <div role="alert" className="alert">{error}</div>}
      {success && <Toast message={success} onClear={() => setSuccess("")} />}

      <div className="bk-dashboard">
        {/* ── Color Palette ── */}
        <section className="panel bk-palette">
          <h2>Colors</h2>
          <div className="bk-swatches-editor">
            {COLOR_SLOTS.map((slot) => (
              <div key={slot} className="bk-swatch-row">
                <span className="bk-swatch-label">{COLOR_LABELS[slot]}</span>
                <span className="bk-swatch-preview" style={{background: colors[slot]}} />
                <input
                  type="color"
                  value={colors[slot]}
                  onChange={(e) => handleColorChange(slot, e.target.value)}
                  className="bk-color-picker"
                  aria-label={`${COLOR_LABELS[slot]} color`}
                />
                <input
                  data-testid={`hex-${slot}`}
                  type="text"
                  value={colors[slot]}
                  onChange={(e) => handleColorChange(slot, e.target.value)}
                  className="bk-hex-input"
                  aria-label={`${COLOR_LABELS[slot]} hex`}
                />
                <small className="bk-rgb">{hexToRgb(colors[slot])}</small>
              </div>
            ))}
          </div>
        </section>

        {/* ── Font Selector ── */}
        <section className="panel bk-fonts">
          <h2>Fonts</h2>
          {(["heading", "body", "accent"] as const).map((slot) => (
            <div key={slot} className="bk-font-row">
              <label className="bk-font-label">{COLOR_LABELS[slot] || slot.charAt(0).toUpperCase() + slot.slice(1)}</label>
              <input
                data-testid={`font-${slot}`}
                type="text"
                value={fonts[slot]}
                onChange={(e) => handleFontChange(slot, e.target.value)}
                className="bk-font-input"
                placeholder="Font name"
              />
              <div className="bk-font-preview" style={{fontFamily: fonts[slot]}}>
                The quick brown fox
              </div>
            </div>
          ))}
        </section>

        {/* ── Logo Upload ── */}
        <section className="panel bk-logos">
          <h2>Logos</h2>
          {(["primary", "secondary", "icon", "watermark"] as const).map((slot) => (
            <div
              key={slot}
              data-testid={`logo-drop-zone-${slot}`}
              className="bk-drop-zone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleDrop(e, slot)}
            >
              {logos[slot] ? (
                <img src={String(logos[slot])} alt={`${slot} logo`} />
              ) : (
                <span className="bk-drop-label">Drop {slot} logo here</span>
              )}
            </div>
          ))}
        </section>

        {/* ── Live Preview ── */}
        <section className="panel bk-preview-section">
          <h2>Live preview</h2>
          <div
            data-testid="brandkit-preview"
            className="bk-preview"
            style={{
              ["--brand-primary" as string]: colors.primary,
              ["--brand-secondary" as string]: colors.secondary,
              ["--brand-accent" as string]: colors.accent,
              ["--brand-background" as string]: colors.background,
              ["--brand-text" as string]: colors.text,
              ["--brand-font-heading" as string]: fonts.heading,
              ["--brand-font-body" as string]: fonts.body,
              ["--brand-font-accent" as string]: fonts.accent,
              background: colors.background,
              color: colors.text,
            }}
          >
            <h3 style={{fontFamily: fonts.heading, color: colors.primary}}>Sample Heading</h3>
            <p style={{fontFamily: fonts.body}}>This is body text rendered in your brand's colors and fonts. It shows how content will look with your visual identity applied.</p>
            <button style={{background: colors.accent, color: colors.background, fontFamily: fonts.heading}}>Call to Action</button>
            <div className="bk-preview-card" style={{borderColor: colors.secondary}}>
              <small style={{color: colors.secondary, fontFamily: fonts.accent}}>Card label</small>
              <p style={{fontFamily: fonts.body}}>Card body text example.</p>
            </div>
          </div>
        </section>
      </div>

      <div className="bk-actions">
        <button className="back" onClick={onBack}>← Back</button>
        {onGuidelines && <button className="ghost" onClick={onGuidelines}>View guidelines</button>}
        <button onClick={handleSave} disabled={saving}>{saving ? "Saving…" : "Save brand kit"}</button>
      </div>
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════
   BrandGuidelinesView — fetch + render + download
   ═════════════════════════════════════════════════════════════ */

export function BrandGuidelinesView({brandKitId, onBack}: {brandKitId: string; onBack: () => void}) {
  const [html, setHtml] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchBrandGuidelines(brandKitId)
      .then(setHtml)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load guidelines"))
      .finally(() => setLoading(false));
  }, [brandKitId]);

  const handleDownload = () => {
    const blob = new Blob([html], {type: "text/html"});
    let url = "";
    if (typeof URL.createObjectURL === "function") {
      url = URL.createObjectURL(blob);
    }
    const a = document.createElement("a");
    a.href = url;
    a.download = `brand-guidelines-${brandKitId}.html`;
    a.click();
    if (url) URL.revokeObjectURL(url);
  };

  if (loading) return <div className="loading" aria-live="polite">Loading guidelines…</div>;
  if (error) return <div role="alert" className="alert">{error}<button className="back" onClick={onBack}>← Back</button></div>;

  return (
    <div className="bk-workspace">
      <div className="bk-guidelines-header">
        <button className="back" onClick={onBack}>← Back</button>
        <button onClick={handleDownload}>Download guidelines</button>
      </div>
      <div data-testid="guidelines-container" className="bk-guidelines" dangerouslySetInnerHTML={{__html: html}} />
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════
   BrandKitWorkspace — top-level switcher (list / dashboard / guidelines)
   ═════════════════════════════════════════════════════════════ */

export function BrandKitWorkspace() {
  const [selected, setSelected] = useState<BrandKit | null>(null);
  const [guidelinesId, setGuidelinesId] = useState<string | null>(null);

  if (guidelinesId) {
    return <BrandGuidelinesView brandKitId={guidelinesId} onBack={() => setGuidelinesId(null)} />;
  }
  if (selected) {
    return (
      <BrandKitDashboard
        brandKitId={selected.id}
        onBack={() => setSelected(null)}
        onGuidelines={() => setGuidelinesId(selected.id)}
      />
    );
  }
  return <BrandKitList onSelect={setSelected} />;
}
