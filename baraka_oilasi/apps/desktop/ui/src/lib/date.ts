/** Yadrodagi `YYYY-MM-DD` ni `15.11.2026` koʻrinishida koʻrsatadi (faqat matn, hisob yoʻq). */
export function showDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}.${m}.${y}` : iso;
}
