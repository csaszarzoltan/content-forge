/* ── Transcreate — cultural adaptation review workspace ─────
   Side-by-side diff (original / literal / adapted), per-segment
   accept / edit / reject controls, low-confidence flagging, and
   export of accepted adaptations.

   API contract (src/routers/transcreation.py):
     POST /api/v1/transcreation/analyze
     POST /api/v1/transcreation/adapt      {text,target_locale,source_locale,
                                            accepted_ids,rejected_ids,edits}
     POST /api/v1/transcreation/preflight
     GET  /api/v1/transcreation/preflight/{asset_id}
     POST /api/v1/transcreation/preflight/{asset_id}/override
     GET  /api/v1/transcreation/assets/{asset_id}/result
     POST /api/v1/transcreation/assets/{asset_id}/export   (409 while flagged)
   ─────────────────────────────────────────────────────────── */

import React, {FormEvent, useState} from "react";
import {validationMessage} from "./flow";

/* Surface the real API detail (e.g. 409 export-blocked) instead of the
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

/* ── types (mirror src/schemas/transcreation.py) ─────────── */

export type RiskCategory = "idiom" | "cultural_reference" | "register" | "taboo";
export type RiskLevel = "low" | "medium" | "high";
export type SegmentDecision = "accept" | "reject" | "edit";
export type FormatType = "date" | "currency" | "unit" | "honorific";

export type RiskItem = {
  id: string;
  segment: string;
  category: RiskCategory;
  original_text: string;
  issue_description: string;
  confidence: number;
  risk_level: RiskLevel;
  suggested_replacement?: string | null;
  locale: string;
};

export type LocaleFormatItem = {
  id?: string | null;
  original: string;
  converted: string;
  format_type: FormatType;
  ambiguous: boolean;
  locale: string;
};

export type AdaptedSegment = {
  id: string;
  original: string;
  literal: string;
  adapted: string;
  risk_item?: RiskItem | null;
  decision?: SegmentDecision | null;
};

export type AdaptResponse = {
  adapted_text: string;
  segments: AdaptedSegment[];
  changes_log: Record<string, unknown>[];
  flagged_segments: string[];
};

export type AnalyzeResponse = {
  risk_items: RiskItem[];
  format_items: LocaleFormatItem[];
  overall_risk: RiskLevel;
  locale: string;
};

export type PreflightResult = {
  asset_id: string;
  risk_items: RiskItem[];
  format_items: LocaleFormatItem[];
  blocked: boolean;
  blocked_reasons: string[];
  audit_status: "pass" | "fail" | "review_needed";
  override_available: boolean;
};

/* ── API helpers ─────────────────────────────────────────── */

async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {"Content-Type": "application/json", ...(options?.headers || {})},
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export async function transcreateAnalyze(
  text: string,
  targetLocale: string,
  sourceLocale = "auto",
): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>("/api/v1/transcreation/analyze", {
    method: "POST",
    body: JSON.stringify({text, target_locale: targetLocale, source_locale: sourceLocale}),
  });
}

export async function transcreateAdapt(
  text: string,
  targetLocale: string,
  sourceLocale: string,
  acceptedIds: string[],
  rejectedIds: string[],
  edits: Record<string, string>,
  assetId?: string,
): Promise<AdaptResponse> {
  const body: Record<string, unknown> = {
    text,
    target_locale: targetLocale,
    source_locale: sourceLocale,
    accepted_ids: acceptedIds,
    rejected_ids: rejectedIds,
    edits,
  };
  if (assetId) body.asset_id = assetId;
  return apiRequest<AdaptResponse>("/api/v1/transcreation/adapt", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function transcreatePreflight(
  assetId: string,
  content: string,
  targetLocale: string,
): Promise<PreflightResult> {
  return apiRequest<PreflightResult>("/api/v1/transcreation/preflight", {
    method: "POST",
    body: JSON.stringify({asset_id: assetId, content, target_locale: targetLocale}),
  });
}

export async function transcreateOverride(assetId: string): Promise<PreflightResult> {
  return apiRequest<PreflightResult>(`/api/v1/transcreation/preflight/${assetId}/override`, {
    method: "POST",
    body: JSON.stringify({override: true}),
  });
}

export async function transcreateExport(assetId: string): Promise<{asset_id: string; adapted_text: string}> {
  return apiRequest<{asset_id: string; adapted_text: string}>(
    `/api/v1/transcreation/assets/${assetId}/export`,
    {method: "POST", body: "{}"},
  );
}

/* ── presentation helpers ────────────────────────────────── */

const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

const DECISION_LABEL: Record<string, string> = {
  accept: "Accepted",
  reject: "Rejected",
  edit: "Edited",
};

const LOCALES = [
  "de-DE", "en-US", "en-GB", "es-ES", "fr-FR", "it-IT", "ja-JP", "pt-BR", "zh-CN",
];

const pretty = (v: unknown): string =>
  String(v ?? "").replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());

const pct = (n: number): string => `${Math.round(n * 100)}%`;

/* ═══════════════════════════════════════════════════════════
   TranscreationWorkspace
   ═══════════════════════════════════════════════════════════ */

export function TranscreationWorkspace({
  assetId,
  initialText,
  initialLocale,
}: {
  assetId?: string;
  initialText?: string;
  initialLocale?: string;
}) {
  const [text, setText] = useState(initialText ?? "");
  const [locale, setLocale] = useState(initialLocale ?? "de-DE");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [adapted, setAdapted] = useState<AdaptResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  // per-segment review state (keyed by segment id)
  const [accepted, setAccepted] = useState<Set<string>>(new Set());
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);

  const clearError = () => setError("");

  const runAdapt = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await transcreateAdapt(
        text,
        locale,
        "auto",
        [...accepted],
        [...rejected],
        edits,
        assetId,
      );
      setAdapted(result);
      setAnalysis(null);
      setPreflight(null);
      setEditingId(null);
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setLoading(false);
    }
  };

  const runAnalyze = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await transcreateAnalyze(text, locale);
      setAnalysis(result);
      setAdapted(null);
      setPreflight(null);
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setLoading(false);
    }
  };

  const runPreflight = async () => {
    if (!assetId || !text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await transcreatePreflight(assetId, text, locale);
      setPreflight(result);
      setAnalysis(null);
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setLoading(false);
    }
  };

  const runOverride = async () => {
    if (!assetId) return;
    setLoading(true);
    setError("");
    try {
      const result = await transcreateOverride(assetId);
      setPreflight(result);
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setLoading(false);
    }
  };

  const runExport = async () => {
    if (!assetId) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = await transcreateExport(assetId);
      setSuccess(`Exported accepted adaptations for asset ${result.asset_id}`);
    } catch (x) {
      setError(apiMessage(x));
    } finally {
      setLoading(false);
    }
  };

  const decide = (seg: AdaptedSegment, decision: "accept" | "reject") => {
    setAccepted((prev) => {
      const next = new Set(prev);
      if (decision === "accept") next.add(seg.id);
      else next.delete(seg.id);
      return next;
    });
    setRejected((prev) => {
      const next = new Set(prev);
      if (decision === "reject") next.add(seg.id);
      else next.delete(seg.id);
      return next;
    });
    setEdits((prev) => {
      const next = {...prev};
      delete next[seg.id];
      return next;
    });
    setEditingId(null);
  };

  const beginEdit = (seg: AdaptedSegment) => {
    setEditingId(seg.id);
    setEdits((prev) => ({...prev, [seg.id]: prev[seg.id] ?? seg.adapted}));
  };

  const commitEdit = (seg: AdaptedSegment) => {
    const value = (edits[seg.id] ?? "").trim();
    if (value) {
      setEditingId(null);
      setAccepted((prev) => {
        const next = new Set(prev);
        next.delete(seg.id);
        return next;
      });
      setRejected((prev) => {
        const next = new Set(prev);
        next.delete(seg.id);
        return next;
      });
      return;
    }
    // empty edit → cancel back to adapted
    setEdits((prev) => {
      const next = {...prev};
      delete next[seg.id];
      return next;
    });
    setEditingId(null);
  };

  const resolvedCount =
    adapted?.segments.filter(
      (s) => accepted.has(s.id) || rejected.has(s.id) || Boolean(edits[s.id]?.trim()),
    ).length ?? 0;
  const unresolvedFlagged =
    adapted?.segments.filter(
      (s) =>
        s.risk_item &&
        s.risk_item.confidence < 0.7 &&
        !accepted.has(s.id) &&
        !rejected.has(s.id) &&
        !(edits[s.id] ?? "").trim(),
    ).length ?? 0;

  const segmentText = (seg: AdaptedSegment): string => {
    if (edits[seg.id]) return edits[seg.id] as string;
    if (accepted.has(seg.id)) return seg.adapted;
    if (rejected.has(seg.id)) return seg.literal;
    return seg.adapted;
  };

  return (
    <div className="tc-workspace">
      <header className="page-head">
        <span className="eyebrow">CULTURAL ADAPTATION</span>
        <h1>Transcreate</h1>
        <p>Adapt content for a target locale: review each segment side by side, then export the accepted version.</p>
      </header>

      {error && (
        <div role="alert" className="alert">
          {error}
          <button className="link" onClick={clearError}>Dismiss</button>
        </div>
      )}
      {success && <div role="status" className="tc-success">{success}</div>}

      <form className="panel tc-input" onSubmit={runAdapt}>
        <div className="tc-input-row">
          <label>
            Source text
            <textarea
              name="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the content you want to culturally adapt…"
              aria-label="Source text"
            />
          </label>
          <label>
            Target locale
            <select value={locale} onChange={(e) => setLocale(e.target.value)}>
              {LOCALES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </label>
        </div>
        <div className="tc-actions">
          <button type="submit" disabled={loading || !text.trim()}>
            {loading ? "Working…" : "Adapt"}
          </button>
          <button type="button" className="ghost" onClick={runAnalyze} disabled={loading || !text.trim()}>
            Analyze risks
          </button>
          {assetId && (
            <button type="button" className="ghost" onClick={runPreflight} disabled={loading || !text.trim()}>
              Preflight
            </button>
          )}
        </div>
      </form>

      {analysis && (
        <section className="panel" aria-label="Risk analysis">
          <div className="panel-title">
            <h2>Analysis</h2>
            <span className="status">{pretty(analysis.overall_risk)} risk</span>
          </div>
          {analysis.risk_items.length === 0 && (
            <p className="muted">No cultural risk items detected for {analysis.locale}.</p>
          )}
          {analysis.risk_items.map((item) => (
            <div className="tc-risk" key={item.id}>
              <span className={`risk-pill risk-${item.risk_level}`}>{RISK_LABEL[item.risk_level]}</span>
              <div>
                <b>{pretty(item.category)}</b>
                <p>{item.issue_description}</p>
                <small className="muted">Confidence {pct(item.confidence)}</small>
              </div>
              {item.suggested_replacement && (
                <span className="tc-replacement">→ {item.suggested_replacement}</span>
              )}
            </div>
          ))}
          {analysis.format_items.length > 0 && (
            <div className="tc-formats">
              <h3>Locale formatting</h3>
              {analysis.format_items.map((f, i) => (
                <div key={f.id ?? i} className="tc-format">
                  <span>{pretty(f.format_type)}</span>
                  <del>{f.original}</del>
                  <i>→</i>
                  <b>{f.converted}</b>
                  {f.ambiguous && <em className="risk-pill risk-medium">ambiguous</em>}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {preflight && (
        <section className="panel" aria-label="Preflight result">
          <div className="panel-title">
            <h2>Preflight — {preflight.asset_id}</h2>
            <Status value={preflight.blocked ? "BLOCKED" : "READY"} />
          </div>
          {preflight.blocked_reasons.map((r) => (
            <div className="blocker" key={r}>! <span>{r}</span></div>
          ))}
          {preflight.blocked && preflight.override_available && (
            <button className="ghost" onClick={runOverride} disabled={loading}>
              Override and publish anyway
            </button>
          )}
        </section>
      )}

      {adapted && (
        <>
          <section className="panel tc-result" aria-label="Adapted result">
            <div className="panel-title">
              <h2>Adapted text</h2>
              {unresolvedFlagged > 0 && (
                <span className="tc-flag-banner">
                  {unresolvedFlagged} low-confidence segment{unresolvedFlagged > 1 ? "s" : ""} flagged for review
                </span>
              )}
              {unresolvedFlagged === 0 && <span className="tc-flag-clear">All segments reviewed</span>}
            </div>
            <p className="tc-adapted" data-testid="adapted-text">{adapted.adapted_text}</p>
          </section>

          <section className="panel" aria-label="Segment review">
            <div className="panel-title">
              <h2>Segment review</h2>
              <span className="muted">{resolvedCount}/{adapted.segments.length} resolved</span>
            </div>
            <div className="tc-seg-head" aria-hidden>
              <span>Original</span>
              <span>Literal</span>
              <span>Adapted</span>
            </div>
            {adapted.segments.map((seg) => {
              const lowConf = Boolean(seg.risk_item && seg.risk_item.confidence < 0.7);
              const resolved = accepted.has(seg.id) || rejected.has(seg.id) || Boolean(edits[seg.id]?.trim());
              return (
                <article
                  key={seg.id}
                  className={`tc-segment${lowConf && !resolved ? " flagged" : ""}${resolved ? " resolved" : ""}`}
                  data-segment-id={seg.id}
                >
                  {lowConf && !resolved && (
                    <div className="tc-flag">
                      <span role="img" aria-label="flag">⚑</span>
                      Low confidence ({pct(seg.risk_item!.confidence)}) — review required
                    </div>
                  )}
                  <div className="tc-cols">
                    <div className="tc-cell">
                      <p>{seg.original}</p>
                      {seg.risk_item && (
                        <div className="tc-risk-meta">
                          <span className={`risk-pill risk-${seg.risk_item.risk_level}`}>
                            {pretty(seg.risk_item.category)}
                          </span>
                          <small className="muted">{seg.risk_item.issue_description}</small>
                        </div>
                      )}
                    </div>
                    <div className="tc-cell">{seg.literal}</div>
                    <div className="tc-cell">
                      {editingId === seg.id ? (
                        <textarea
                          value={edits[seg.id] ?? ""}
                          onChange={(e) => setEdits((prev) => ({...prev, [seg.id]: e.target.value}))}
                          aria-label={`Edit ${seg.id}`}
                        />
                      ) : (
                        <p className={edits[seg.id] ? "tc-edit-text" : ""}>{segmentText(seg)}</p>
                      )}
                    </div>
                  </div>
                  <footer className="tc-seg-footer">
                    <span className="tc-seg-id">{seg.id}</span>
                    {seg.decision && <span className="tc-decision">{DECISION_LABEL[seg.decision]}</span>}
                    <div className="tc-seg-btns">
                      {editingId === seg.id ? (
                        <>
                          <button className="ghost" onClick={() => commitEdit(seg)}>Save edit</button>
                          <button className="ghost" onClick={() => setEditingId(null)}>Cancel</button>
                        </>
                      ) : (
                        <>
                          <button
                            className={accepted.has(seg.id) ? "tc-active" : "ghost"}
                            onClick={() => decide(seg, "accept")}
                          >
                            ✓ Accept
                          </button>
                          <button className="ghost" onClick={() => beginEdit(seg)}>✎ Edit</button>
                          <button
                            className={rejected.has(seg.id) ? "tc-active tc-reject" : "ghost"}
                            onClick={() => decide(seg, "reject")}
                          >
                            ✕ Reject
                          </button>
                        </>
                      )}
                    </div>
                  </footer>
                </article>
              );
            })}
          </section>

          <div className="tc-export-bar">
            <button onClick={runAdapt} disabled={loading}>Re-run adaptation</button>
            {assetId && (
              <button onClick={runExport} disabled={loading || unresolvedFlagged > 0}>
                Export accepted adaptations
              </button>
            )}
            {assetId && unresolvedFlagged > 0 && (
              <span className="muted">Resolve all flagged segments to unlock export</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

const Status = ({value}: {value: unknown}) => <span className="status">{pretty(value)}</span>;
