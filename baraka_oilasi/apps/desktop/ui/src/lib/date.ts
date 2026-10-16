/** Yadrodagi `YYYY-MM-DD` ni `15.11.2026` koʻrinishida koʻrsatadi (faqat matn, hisob yoʻq). */
export function showDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}.${m}.${y}` : iso;
}

/** `YYYY-MM-01` → `06.2027`. */
export function showMonth(iso: string): string {
  const [y, m] = iso.split("-");
  return y && m ? `${m}.${y}` : iso;
}

const pad = (n: number) => String(n).padStart(2, "0");

/** Sana maydoni uchun boshlang'ich qiymat (faqat ko'rsatish, hisob emas). */
export function todayText(): string {
  const d = new Date();
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}
