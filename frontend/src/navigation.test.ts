import {describe, expect, it} from "vitest";
import {NAV_ITEMS, normalizeRoute} from "./navigation";

describe("workspace navigation", () => {
  it("gives every visible workspace a real route", () => {
    expect(NAV_ITEMS.map(item => item.route)).toEqual([
      "my-work", "campaigns", "content", "calendar", "approvals",
      "localization", "analytics", "brand", "connections", "admin"
    ]);
  });
  it("normalizes hashes and falls back safely", () => {
    expect(normalizeRoute("#campaigns")).toBe("campaigns");
    expect(normalizeRoute("#missing")).toBe("my-work");
  });
});
