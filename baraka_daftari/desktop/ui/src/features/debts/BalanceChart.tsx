import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useRef } from 'react';

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);

export interface Series {
  name: string;
  /** Oyma-oy qoldiq (so'm, faqat chizish uchun; hisob-kitob Rustda). */
  values: number[];
}

/** Qoldiq grafigi: odatiy va tezlashtirilgan jadval yonma-yon. Faqat ko'rsatish — pul hisobi yo'q. */
export function BalanceChart({ series, label }: { series: Series[]; label: string }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current) return;
    const chart = echarts.init(el.current);
    const months = Math.max(0, ...series.map((s) => s.values.length));
    chart.setOption({
      aria: { enabled: true },
      tooltip: { trigger: 'axis' },
      legend: { data: series.map((s) => s.name) },
      grid: { left: 70, right: 16, top: 36, bottom: 28 },
      xAxis: { type: 'category', data: Array.from({ length: months }, (_, i) => i + 1) },
      yAxis: { type: 'value' },
      series: series.map((s) => ({
        name: s.name,
        type: 'line',
        data: s.values,
        showSymbol: false,
      })),
    });
    const onResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
    };
  }, [series]);
  return <div ref={el} role="img" aria-label={label} className="h-64 w-full" />;
}
