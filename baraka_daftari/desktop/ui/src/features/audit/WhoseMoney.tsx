import { useTranslation } from 'react-i18next';

import type { OverviewDto } from '../../bindings';
import { formatBp } from '../../lib/api';

function Row({
  label,
  amount,
  bp,
  strong,
}: {
  label: string;
  amount: string;
  bp: number;
  strong?: boolean;
}) {
  const width = Math.min(100, bp / 100);
  return (
    <li className="py-1">
      <div className={`flex justify-between ${strong === true ? 'font-semibold' : ''}`}>
        <span>{label}</span>
        <span>
          {amount} · {formatBp(bp)}
        </span>
      </div>
      <div className="mt-1 h-2 rounded bg-accent/10" aria-hidden="true">
        <div className="h-2 rounded bg-accent" style={{ width: `${String(width)}%` }} />
      </div>
    </li>
  );
}

/** "Kimning puli?": oylik daromad egalarga bo'lingan; birinchi qator — o'zingiz. */
export function WhoseMoney({ overview }: { overview: OverviewDto }) {
  const { t } = useTranslation();
  return (
    <section aria-label={t('whose.title')}>
      <h2 className="text-lg font-semibold">{t('whose.title')}</h2>
      <ul>
        <Row
          label={t('whose.you')}
          amount={overview.savings.formatted}
          bp={overview.self_paid_bp}
          strong
        />
        {overview.owners.map((o) => (
          <Row
            key={o.owner ?? 'none'}
            label={t(`owner.${o.owner ?? 'OTHER'}`)}
            amount={o.amount.formatted}
            bp={o.bp}
          />
        ))}
      </ul>
    </section>
  );
}
