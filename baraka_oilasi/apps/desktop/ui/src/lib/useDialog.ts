import { useEffect, useRef } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal oyna uchun klaviatura qoidalari (WCAG 2.1.2, 2.4.3): ochilganda fokus ichkariga,
 * `Tab` oyna ichida aylanadi, `Esc` yopadi, yopilganda fokus avvalgi joyiga qaytadi.
 * `role="dialog"` elementiga `ref` qilib beriladi.
 */
export function useDialog<T extends HTMLElement>(onClose: () => void) {
  const ref = useRef<T>(null);
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const el = ref.current;
    const before = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (el && !el.contains(document.activeElement)) {
      const auto = el.querySelector<HTMLElement>("[autofocus]") ?? el.querySelector<HTMLElement>(FOCUSABLE);
      (auto ?? el).focus();
    }
    const onKey = (e: KeyboardEvent) => {
      if (!el) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        close.current();
      } else if (e.key === "Tab") {
        const items = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE));
        const first = items[0];
        const last = items[items.length - 1];
        if (!first || !last) return;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    el?.addEventListener("keydown", onKey);
    return () => {
      el?.removeEventListener("keydown", onKey);
      if (before?.isConnected) before.focus();
    };
  }, []);

  return ref;
}
