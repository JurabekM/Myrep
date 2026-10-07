import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';

import type { ScheduleRowDto } from '../../bindings';

const ROW_H = 30;

/** Katta jadval: virtualizatsiya bilan (1200 oygacha), faqat ko'rinadigan qatorlar chiziladi. */
export function ScheduleTable({ rows }: { rows: ScheduleRowDto[] }) {
  const { t } = useTranslation();
  const parent = useRef<HTMLDivElement>(null);
  const virtual = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parent.current,
    estimateSize: () => ROW_H,
    overscan: 8,
    initialRect: { width: 640, height: 320 },
  });
  // Maket o'lchami noma'lum muhitda (masalan, testda) birinchi qatorlar baribir chiziladi.
  const items = virtual.getVirtualItems();
  const shown =
    items.length > 0
      ? items
      : rows.slice(0, 30).map((_, index) => ({ index, start: index * ROW_H }));
  return (
    <div
      role="table"
      aria-label={t('calc.table')}
      aria-rowcount={rows.length + 1}
      className="text-sm"
    >
      <div role="row" className="grid grid-cols-5 border-b border-accent/40 font-semibold">
        {(['month', 'interest', 'principal', 'extra', 'balance'] as const).map((c) => (
          <div key={c} role="columnheader" className={c === 'month' ? '' : 'text-right'}>
            {t(`calc.cols.${c}`)}
          </div>
        ))}
      </div>
      <div ref={parent} className="h-80 overflow-auto" data-testid="schedule-scroll">
        <div style={{ height: virtual.getTotalSize(), position: 'relative' }}>
          {shown.map((v) => {
            const r = rows[v.index];
            if (!r) return null;
            return (
              <div
                key={r.month}
                role="row"
                aria-rowindex={v.index + 2}
                className="grid grid-cols-5"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: ROW_H,
                  transform: `translateY(${String(v.start)}px)`,
                }}
              >
                <div role="cell">{r.month}</div>
                <div role="cell" className="text-right">
                  {r.interest.formatted}
                </div>
                <div role="cell" className="text-right">
                  {r.principal.formatted}
                </div>
                <div role="cell" className="text-right">
                  {r.extra.formatted}
                </div>
                <div role="cell" className="text-right">
                  {r.balance.formatted}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
