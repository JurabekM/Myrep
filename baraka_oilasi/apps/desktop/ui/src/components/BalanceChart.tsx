import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { TimelinePointDto } from "../bindings";
import { showMonth } from "../lib/date";

const W = 640;
const H = 240;
const PAD = { top: 16, right: 96, bottom: 28, left: 12 };

/**
 * Umumiy qoldiq: odatiy va qoʻshimcha toʻlovli prognoz (bitta oʻq, ikki chiziq).
 * Qiymatlar faqat chizish uchun songa aylantiriladi; matnlar yadrodagi `formatted` dan.
 */
export function BalanceChart({ points }: { points: TimelinePointDto[] }) {
  const { t } = useTranslation();
  const [hover, setHover] = useState<number | null>(null);
  if (points.length === 0) return null;
  const base = points.map((p) => Number(p.baseBalance.minor));
  const fast = points.map((p) => Number(p.acceleratedBalance.minor));
  const max = Math.max(...base, ...fast, 1);
  const iw = W - PAD.left - PAD.right;
  const ih = H - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (points.length === 1 ? 0 : (i / (points.length - 1)) * iw);
  const y = (v: number) => PAD.top + ih - (v / max) * ih;
  const path = (vs: number[]) => vs.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const fastEnd = fast.findIndex((v) => v === 0);
  const fastLast = fastEnd === -1 ? fast.length - 1 : fastEnd;
  const top = points[0];
  const h = hover === null ? null : points[hover];

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = PAD.left + ((e.clientX - r.left) / r.width) * iw;
    // Eng yaqin nuqta (piksel masofasi bo'yicha; yaxlitlash yo'q).
    let best = 0;
    points.forEach((_, i) => {
      if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i;
    });
    setHover(best);
  };

  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="flex flex-wrap items-center gap-4 text-sm text-ink-muted">
        <span>{t("payoff.chart.title")}</span>
        <span className="flex items-center gap-2"><span className="inline-block h-0.5 w-5 bg-chart1" />{t("payoff.chart.base")}</span>
        <span className="flex items-center gap-2"><span className="inline-block h-0.5 w-5 bg-chart2" />{t("payoff.chart.accelerated")}</span>
      </figcaption>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={t("payoff.chart.aria")}>
          {[0, 0.5, 1].map((f) => (
            <line key={f} x1={PAD.left} x2={PAD.left + iw} y1={PAD.top + ih * f} y2={PAD.top + ih * f} className="stroke-line" strokeWidth={1} />
          ))}
          <text x={PAD.left + iw + 6} y={PAD.top + 4} className="fill-ink-muted text-[11px]">{top?.baseBalance.formatted}</text>
          <text x={PAD.left + iw + 6} y={PAD.top + ih + 4} className="fill-ink-muted text-[11px]">0</text>
          <text x={PAD.left} y={H - 8} className="fill-ink-muted text-[11px]">{top ? showMonth(top.month) : ""}</text>
          <text x={PAD.left + iw} y={H - 8} textAnchor="end" className="fill-ink-muted text-[11px]">{showMonth(points[points.length - 1]?.month ?? "")}</text>
          <path d={path(base)} fill="none" className="stroke-chart1" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          <path d={path(fast.slice(0, fastLast + 1))} fill="none" className="stroke-chart2" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          <circle cx={x(fastLast)} cy={y(0)} r={4} className="fill-chart2 stroke-surface" strokeWidth={2} />
          {hover !== null && (
            <>
              <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + ih} className="stroke-ink-muted" strokeWidth={1} />
              <circle cx={x(hover)} cy={y(base[hover] ?? 0)} r={4} className="fill-chart1 stroke-surface" strokeWidth={2} />
              <circle cx={x(hover)} cy={y(fast[hover] ?? 0)} r={4} className="fill-chart2 stroke-surface" strokeWidth={2} />
            </>
          )}
          <rect x={PAD.left} y={PAD.top} width={iw} height={ih} fill="transparent" onMouseMove={onMove} onMouseLeave={() => setHover(null)} />
        </svg>
        {h && hover !== null && (
          <div
            role="status"
            className="pointer-events-none absolute top-2 rounded-md border border-line bg-sidebar px-3 py-2 text-xs shadow"
            style={{ left: `${Math.min(70, (x(hover) / W) * 100)}%` }}
          >
            <p className="mb-1 font-semibold">{showMonth(h.month)}</p>
            <p className="flex items-center gap-2"><span className="inline-block h-0.5 w-3 bg-chart1" />{t("payoff.chart.base")}: {h.baseBalance.formatted}</p>
            <p className="flex items-center gap-2"><span className="inline-block h-0.5 w-3 bg-chart2" />{t("payoff.chart.accelerated")}: {h.acceleratedBalance.formatted}</p>
          </div>
        )}
      </div>
    </figure>
  );
}
