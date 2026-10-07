import { useTranslation } from 'react-i18next';

import { RescuePanel, useRescue } from './RescuePanel';

export function RescuePage() {
  const { t } = useTranslation();
  const rescue = useRescue();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t('nav.rescue')}</h1>
      <p className="text-sm opacity-80">{t('rescue.hint')}</p>
      <RescuePanel />
      <ul className="divide-y divide-accent/20">
        {rescue.data?.items.map((i) => (
          <li key={i.id} className="flex justify-between py-2">
            <span>
              {t(`rescue.kind.${i.kind}`)}
              {i.note ? ` · ${i.note}` : ''}
            </span>
            <span>
              {i.amount.formatted} {i.transferred ? `✓ ${t('rescue.transferred')}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
