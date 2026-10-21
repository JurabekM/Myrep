import axe from "axe-core";

/**
 * Ekranni axe-core bilan tekshiradi (WCAG 2.x A/AA qoidalari). `color-contrast` jsdom'da
 * hisoblanmaydi — kontrast `cargo xtask tokens` da tokenlar bo'yicha tekshiriladi.
 * Natija — o'qiladigan qatorlar: `qoida: element`.
 */
export async function axeViolations(container: HTMLElement): Promise<string[]> {
  const res = await axe.run(container, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] },
    rules: { "color-contrast": { enabled: false } },
  });
  return res.violations.flatMap((v) => v.nodes.map((n) => `${v.id}: ${n.html.slice(0, 120)}`));
}
