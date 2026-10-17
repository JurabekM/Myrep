import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

/** Karta: bir bo'lim, sarlavha va mazmun. */
export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`flex flex-col gap-4 rounded-xl border border-border bg-surface p-6 ${className}`}
    >
      {title !== undefined ? <h2 className="text-base font-semibold text-text">{title}</h2> : null}
      {children}
    </section>
  );
}

/** Sahifa sarlavhasi va qisqa izoh. */
export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="flex flex-col gap-2">
      <h1 className="text-3xl font-semibold tracking-tight text-text">{title}</h1>
      {subtitle !== undefined ? (
        <p className="max-w-prose text-base text-muted">{subtitle}</p>
      ) : null}
    </header>
  );
}

/** Asosiy tugma (harakat). */
export function PrimaryButton({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={`h-10 rounded-lg bg-accent px-4 text-sm font-medium text-app transition-opacity hover:opacity-90 disabled:opacity-40 ${className}`}
    />
  );
}

/** Ikkinchi darajali tugma. */
export function SecondaryButton({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={`h-10 rounded-lg border border-border px-4 text-sm text-text transition-colors hover:bg-raised disabled:opacity-40 ${className}`}
    />
  );
}

/** Matn maydoni: yorliq bilan. */
export function Field({
  id,
  label,
  className = "",
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { id: string; label: string }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm text-muted">
        {label}
      </label>
      <input
        id={id}
        // Moliyaviy maydonlarda brauzer avtoto'ldirishi yo'q: eski summa taklifi tugmalarni yopib qo'yadi.
        autoComplete="off"
        {...input}
        className={`h-10 rounded-lg border border-border bg-app px-3 text-text outline-none transition-colors focus:border-accent disabled:opacity-50 ${className}`}
      />
    </div>
  );
}

/** Xato yoki ogohlantirish matni (rol: alert). */
export function Alert({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="text-sm text-danger">
      {children}
    </p>
  );
}

/** Ko'rsatkich (yorliq va katta qiymat). */
export function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-2xl font-semibold tracking-tight text-text">{value}</span>
      {hint !== undefined ? <span className="text-xs text-subtle">{hint}</span> : null}
    </div>
  );
}
