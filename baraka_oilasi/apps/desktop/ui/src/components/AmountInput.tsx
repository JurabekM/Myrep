import type { InputHTMLAttributes } from "react";

/** Summa kiritish: matn sifatida qoladi va yadroda parse qilinadi (UI hisoblamaydi). */
export function AmountInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "inputMode">) {
  return <input {...props} type="text" inputMode="decimal" autoComplete="off" className="field text-lg tabular-nums" />;
}
