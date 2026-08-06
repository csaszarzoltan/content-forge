import {describe, expect, it} from "vitest";
import {NAV_ITEMS, normalizeRoute} from "./navigation";

describe("workspace navigation", () => {
  it("gives every visible workspace a real route", () => {
    expect(NAV_ITEMS.map(item => item.route)).toEqual([
      "my-work", "campaigns", "content", "calendar", "approvals",
      "localization", "analytics", "brand", "brand-kit", "connections", "admin"
    ]);
  });
  it("normalizes hashes and falls back safely", () => {
    expect(normalizeRoute("")).toBe("my-work");
    expect(normalizeRoute("#missing")).toBe("my-work");
    expect(normalizeRoute("#brand-kit")).toBe("brand-kit");
  });
  it("places brand-kit after brand with the correct icon", () => {
    const brandIdx = NAV_ITEMS.findIndex(i => i.route === "brand");
    const kitIdx = NAV_ITEMS.findIndex(i => i.route === "brand-kit");
    expect(kitIdx).toBe(brandIdx + 1);
    expect(NAV_ITEMS[kitIdx].label).toBe("Brand Kit");
    expect(NAV_ITEMS[kitIdx].icon).toBe("◆");
  });
});
