import type { ReactNode } from "react";
import { BrandMark } from "../components/BrandMark";
import { PIN_LENGTH, sanitizePin } from "./pin";

interface SecurityCardProps {
  title: string;
  text: string;
  children: ReactNode;
}

/** PIN ekranlarining umumiy ko'rinishi: markazda karta, sarlavha va forma. */
export function SecurityCard({ title, text, children }: SecurityCardProps) {
  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <section className="flex w-full max-w-sm flex-col gap-6 rounded-xl border border-border bg-surface p-8">
        <BrandMark className="size-10" />
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-text">{title}</h1>
          <p className="text-sm text-muted">{text}</p>
        </header>
        {children}
      </section>
    </div>
  );
}

interface PinFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoFocus?: boolean;
  disabled?: boolean;
}

/** 6 raqamli PIN maydoni. Faqat raqam qabul qiladi; matn yashiriladi (type=password). */
export function PinField({ id, label, value, onChange, autoFocus, disabled }: PinFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm text-muted">
        {label}
      </label>
      <input
        id={id}
        type="password"
        inputMode="numeric"
        autoComplete="off"
        autoFocus={autoFocus}
        disabled={disabled}
        maxLength={PIN_LENGTH}
        value={value}
        onChange={(event) => {
          onChange(sanitizePin(event.target.value));
        }}
        className="h-11 w-full rounded-lg border border-border bg-app px-4 text-center text-lg tracking-[0.5em] text-text outline-none transition-colors focus:border-accent disabled:opacity-50"
      />
    </div>
  );
}
