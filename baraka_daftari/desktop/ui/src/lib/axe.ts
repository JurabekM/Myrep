import axe from 'axe-core';

/**
 * Accessibility buzilishlari ro'yxati (matn). jsdom'da rang kontrasti hisoblanmaydi, shuning uchun
 * `color-contrast` o'chirilgan: kontrast qo'lda (RELEASE_CHECKLIST) va High Contrast CSS bilan hal etiladi.
 */
export async function a11yViolations(node: HTMLElement): Promise<string[]> {
  const result = await axe.run(node, { rules: { 'color-contrast': { enabled: false } } });
  return result.violations.map(
    (v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`,
  );
}
