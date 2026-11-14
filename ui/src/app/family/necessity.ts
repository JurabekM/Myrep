/** Toifa kodlari (backend `Necessity::code`). */
export const NECESSITY_CODES = ["ZARUR", "KERAK", "HAVAS"] as const;

export type NecessityCode = (typeof NECESSITY_CODES)[number];

/** Toifa tarjima kalitlari. Kod noma'lum bo'lsa — `KERAK` (SPEC 2B.2: standart). */
export const NECESSITY_KEYS = {
  ZARUR: "family.zarur",
  KERAK: "family.kerak",
  HAVAS: "family.havas",
} as const;

export function necessityKey(code: string): (typeof NECESSITY_KEYS)[NecessityCode] {
  if (code === "ZARUR") {
    return NECESSITY_KEYS.ZARUR;
  }
  if (code === "HAVAS") {
    return NECESSITY_KEYS.HAVAS;
  }
  return NECESSITY_KEYS.KERAK;
}
