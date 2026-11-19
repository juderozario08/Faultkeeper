import { describe, expect, it } from "vitest";
import { contrastRatio } from "./contrast";
import { BACKGROUND_TOKENS, TEXT_TOKENS, tokens, type ThemeName } from "./tokens";

describe("theme contrast (WCAG AA, ADR 0012)", () => {
  it("computes known ratios", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(contrastRatio("#565f89", "#1a1b26")).toBeCloseTo(2.76, 1);
  });

  for (const theme of ["dark", "light"] as ThemeName[]) {
    for (const text of TEXT_TOKENS) {
      for (const background of BACKGROUND_TOKENS) {
        it(`${theme}: ${text} on ${background} >= 4.5`, () => {
          const ratio = contrastRatio(tokens[theme][text], tokens[theme][background]);
          expect(ratio).toBeGreaterThanOrEqual(4.5);
        });
      }
    }
    it(`${theme}: button label on accent >= 4.5`, () => {
      expect(contrastRatio(tokens[theme].onAccent, tokens[theme].accentText)).toBeGreaterThanOrEqual(4.5);
    });
  }
});
