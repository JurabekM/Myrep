import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { homeSlots } from './slots';

export function HomePage() {
  const { t } = useTranslation();
  const { data, error } = useQuery({
    queryKey: ['home'],
    queryFn: () => unwrap(commands.homeSummary()),
  });
  if (error) return <p role="alert">{errorMessage(t, error)}</p>;
  if (!data) return null;
  return (
    <div>
      <h1 className="text-2xl font-semibold">{t('nav.home')}</h1>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {homeSlots.map(({ id, Component }) => (
          <Component key={id} home={data} />
        ))}
      </div>
    </div>
  );
}
