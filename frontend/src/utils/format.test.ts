import { describe, expect, it } from "vitest";
import { formatCount, timeAgo } from "./format";

describe("format", () => {
  it("formats relative time", () => {
    const now = Date.parse("2026-11-18T12:00:00Z");
    expect(timeAgo("2026-11-18T11:59:55Z", now)).toBe("just now");
    expect(timeAgo("2026-11-18T11:55:00Z", now)).toBe("5 minutes ago");
    expect(timeAgo("2026-11-17T12:00:00Z", now)).toBe("yesterday");
  });

  it("abbreviates counts", () => {
    expect(formatCount(999)).toBe("999");
    expect(formatCount(1500)).toBe("1.5k");
    expect(formatCount(25_000)).toBe("25k");
    expect(formatCount(2_300_000)).toBe("2.3M");
  });
});
