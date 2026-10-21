import { type PointerEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Stroke } from "../bindings";
import { useDialog } from "../lib/useDialog";

/** Yadrodagi imzo maydoni (`baraka_agreements::PAD_WIDTH × PAD_HEIGHT`). */
const PAD_W = 1000;
const PAD_H = 400;

/**
 * Shu qurilmada imzo chizish (sichqoncha, pero yoki barmoq). Nuqtalar 0..1000 × 0..400 butun
 * sonlarga keltiriladi; tekshiruv va SVG yadroda.
 */
export function SignaturePad({ name, onSave, onCancel, busy }: { name: string; onSave: (s: Stroke[]) => void; onCancel: () => void; busy: boolean }) {
  const { t } = useTranslation();
  const dialog = useDialog<HTMLDivElement>(onCancel);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const drawing = useRef(false);

  const point = (e: PointerEvent<HTMLCanvasElement>): [number, number] => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = Math.trunc(((e.clientX - r.left) / r.width) * PAD_W);
    const y = Math.trunc(((e.clientY - r.top) / r.height) * PAD_H);
    return [Math.min(PAD_W, Math.max(0, x)), Math.min(PAD_H, Math.max(0, y))];
  };
  const draw = (all: Stroke[]) => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, PAD_W, PAD_H);
    ctx.lineWidth = 8;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#1F1E1D";
    for (const s of all) {
      ctx.beginPath();
      s.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
      ctx.stroke();
    }
  };
  const down = (e: PointerEvent<HTMLCanvasElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drawing.current = true;
    const next = [...strokes, [point(e)]];
    setStrokes(next);
    draw(next);
  };
  const move = (e: PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const p = point(e);
    const next = strokes.map((s, i) => (i === strokes.length - 1 ? [...s, p] : s));
    setStrokes(next);
    draw(next);
  };
  const up = () => {
    drawing.current = false;
  };

  return (
    <div ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-label={t("partnership.sign.title", { name })} className="fixed inset-0 z-20 flex items-center justify-center bg-black/60 p-4">
      <div className="card flex w-full max-w-2xl flex-col gap-3">
        <h2 className="text-lg font-semibold">{t("partnership.sign.title", { name })}</h2>
        <p className="text-sm text-ink-muted">{t("partnership.sign.hint")}</p>
        {/* Imzo qogʻozdagidek oq fonda — PDF bilan bir xil koʻrinadi. */}
        <canvas
          ref={canvas}
          width={PAD_W}
          height={PAD_H}
          aria-label={t("partnership.sign.pad")}
          className="aspect-[5/2] w-full touch-none rounded border border-line bg-[#FAF9F5]"
          onPointerDown={down}
          onPointerMove={move}
          onPointerUp={up}
          onPointerLeave={up}
        />
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={busy || strokes.length === 0} onClick={() => onSave(strokes)}>
            {t("partnership.sign.save")}
          </button>
          <button
            className="btn-ghost"
            onClick={() => {
              setStrokes([]);
              draw([]);
            }}
          >
            {t("partnership.sign.clear")}
          </button>
          <button className="btn-ghost" onClick={onCancel}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
