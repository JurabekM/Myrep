import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { useNav } from '../../app/nav';
import { commands, type IdeaDto } from '../../bindings';
import { errorMessage, percentToBp, unwrap } from '../../lib/api';

function IdeaCard({ i }: { i: IdeaDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const setPage = useNav((s) => s.setPage);
  const [provider, setProvider] = useState('');
  const remove = useMutation({
    mutationFn: () => unwrap(commands.removeCraftIdea(i.id)),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  const draft = useMutation({
    mutationFn: () => unwrap(commands.craftToContract(i.id, provider)),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      setPage('partnerships');
    },
  });
  const names = ['pess', 'avg', 'opt'] as const;
  const error = [remove.error, draft.error].find((e) => e !== null);
  return (
    <li className="py-3" data-testid={`idea-${i.name}`}>
      <div className="flex flex-wrap justify-between gap-2">
        <strong>{i.name}</strong>
        <span>{t('craft.capex', { amount: i.capex_total.formatted })}</span>
      </div>
      {i.note && <p className="text-sm opacity-80">{i.note}</p>}
      <table className="mt-1 w-full text-sm">
        <thead>
          <tr className="text-left">
            <th>{t('craft.scenario')}</th>
            <th className="text-right">{t('craft.net')}</th>
            {i.share_bp !== null && <th className="text-right">{t('craft.afterShare')}</th>}
            <th className="text-right">{t('craft.payback')}</th>
          </tr>
        </thead>
        <tbody>
          {i.scenarios.map((s, k) => (
            <tr key={names[k]} data-testid={`sc-${i.name}-${names[k] ?? ''}`}>
              <td>{t(`craft.scenarios.${names[k] ?? 'avg'}`)}</td>
              <td className="text-right">{s.net.formatted}</td>
              {i.share_bp !== null && <td className="text-right">{s.net_after_share.formatted}</td>}
              <td className="text-right">
                {s.payback_months === null
                  ? t('craft.never')
                  : t('craft.months', { n: s.payback_months })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-2 flex flex-wrap items-end gap-2 text-sm">
        <label className="block">
          {t('craft.providerName')}
          <input
            className="mt-1 block w-40 rounded border border-line-strong bg-transparent p-1"
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
            }}
          />
        </label>
        <button
          type="button"
          className="rounded border border-accent px-3 py-1 disabled:opacity-50"
          disabled={provider.trim() === ''}
          onClick={() => {
            draft.mutate();
          }}
        >
          {t('craft.toContract')}
        </button>
        <button
          type="button"
          className="underline"
          onClick={() => {
            remove.mutate();
          }}
        >
          {t('debts.remove')}
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </li>
  );
}

function IdeaForm() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [note, setNote] = useState('');
  const [capex, setCapex] = useState([{ item: '', price: '' }]);
  const [income, setIncome] = useState(['', '', '']);
  const [expense, setExpense] = useState(['', '', '']);
  const [share, setShare] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const add = useMutation({
    mutationFn: () => {
      const bp = share.trim() === '' ? null : percentToBp(share);
      if (share.trim() !== '' && bp === null) throw new Error('percent');
      return unwrap(
        commands.addCraftIdea({
          name,
          note: note.trim() === '' ? null : note,
          capex: capex.filter((c) => c.item.trim() !== ''),
          income,
          expense,
          share_bp: bp,
        }),
      );
    },
    onSuccess: async () => {
      setName('');
      setNote('');
      setCapex([{ item: '', price: '' }]);
      setIncome(['', '', '']);
      setExpense(['', '', '']);
      setShare('');
      await queryClient.invalidateQueries();
    },
  });
  const inp = 'mt-1 block rounded border border-line-strong bg-transparent p-1';
  const labels = ['pess', 'avg', 'opt'] as const;
  return (
    <form
      className="space-y-3"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        setLocalError(null);
        add.mutate(undefined, {
          onError: (err) => {
            if (err instanceof Error && err.message === 'percent')
              setLocalError(t('partner.badPercent'));
          },
        });
      }}
    >
      <div className="flex flex-wrap gap-3">
        <label className="block text-sm">
          {t('craft.name')}
          <input
            className={`${inp} w-52`}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('craft.noteLabel')}
          <input
            className={`${inp} w-64`}
            value={note}
            onChange={(e) => {
              setNote(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('craft.share')}
          <input
            inputMode="decimal"
            className={`${inp} w-24`}
            value={share}
            onChange={(e) => {
              setShare(e.target.value);
            }}
          />
        </label>
      </div>
      <fieldset className="text-sm">
        <legend className="font-medium">{t('craft.capexTitle')}</legend>
        {capex.map((c, k) => (
          <div key={k} className="mt-1 flex gap-2">
            <input
              aria-label={t('craft.capexItem', { k: k + 1 })}
              className="flex-1 rounded border border-line-strong bg-transparent p-1"
              value={c.item}
              onChange={(e) => {
                setCapex((p) => p.map((x, j) => (j === k ? { ...x, item: e.target.value } : x)));
              }}
            />
            <input
              aria-label={t('craft.capexPrice', { k: k + 1 })}
              inputMode="decimal"
              className="w-36 rounded border border-line-strong bg-transparent p-1"
              value={c.price}
              onChange={(e) => {
                setCapex((p) => p.map((x, j) => (j === k ? { ...x, price: e.target.value } : x)));
              }}
            />
          </div>
        ))}
        <button
          type="button"
          className="mt-1 underline"
          onClick={() => {
            setCapex((p) => [...p, { item: '', price: '' }]);
          }}
        >
          {t('craft.capexAdd')}
        </button>
      </fieldset>
      <div className="grid gap-2 sm:grid-cols-3 text-sm">
        {labels.map((l, k) => (
          <fieldset key={l} className="rounded border border-line p-2">
            <legend className="px-1">{t(`craft.scenarios.${l}`)}</legend>
            <label className="block">
              {t('craft.income', { s: t(`craft.scenarios.${l}`) })}
              <input
                inputMode="decimal"
                className={`${inp} w-full`}
                value={income[k] ?? ''}
                onChange={(e) => {
                  setIncome((p) => p.map((x, j) => (j === k ? e.target.value : x)));
                }}
              />
            </label>
            <label className="block">
              {t('craft.expense', { s: t(`craft.scenarios.${l}`) })}
              <input
                inputMode="decimal"
                className={`${inp} w-full`}
                value={expense[k] ?? ''}
                onChange={(e) => {
                  setExpense((p) => p.map((x, j) => (j === k ? e.target.value : x)));
                }}
              />
            </label>
          </fieldset>
        ))}
      </div>
      {(localError ?? add.error) &&
      !(add.error instanceof Error && add.error.message === 'percent') ? (
        <p role="alert" className="text-sm">
          {localError ?? errorMessage(t, add.error)}
        </p>
      ) : localError ? (
        <p role="alert" className="text-sm">
          {localError}
        </p>
      ) : null}
      <button
        type="submit"
        className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
        disabled={name.trim() === ''}
      >
        {t('craft.save')}
      </button>
    </form>
  );
}

/** «Kafolatlangan foyda» detektori (SPEC 2E.5): tekshiruv ro'yxati → yashil / sariq / qizil. */
function OfferCheck() {
  const { t } = useTranslation();
  const [a, setA] = useState({
    guaranteed_profit: false,
    loss_shared: true,
    real_goods_or_work: true,
    requires_recruiting: false,
    pressure_to_hurry: false,
    written_contract: true,
  });
  const check = useMutation({ mutationFn: () => commands.checkOffer(a) });
  const Q = [
    ['guaranteed_profit', 'offer.q.guaranteed'],
    ['loss_shared', 'offer.q.lossShared'],
    ['real_goods_or_work', 'offer.q.real'],
    ['requires_recruiting', 'offer.q.recruit'],
    ['pressure_to_hurry', 'offer.q.pressure'],
    ['written_contract', 'offer.q.written'],
  ] as const;
  const r = check.data;
  return (
    <section className="rounded-lg border border-line p-5" data-testid="offer">
      <h2 className="font-semibold">{t('offer.title')}</h2>
      <p className="text-sm opacity-80">{t('offer.hint')}</p>
      <ul className="mt-2 space-y-1 text-sm">
        {Q.map(([k, key]) => (
          <li key={k}>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={a[k]}
                onChange={(e) => {
                  setA((p) => ({ ...p, [k]: e.target.checked }));
                }}
              />
              {t(key)}
            </label>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="mt-2 rounded border border-accent px-3 py-1"
        onClick={() => {
          check.mutate();
        }}
      >
        {t('offer.run')}
      </button>
      {r && (
        <div
          className="mt-3 rounded border-2 border-current p-3"
          data-testid="verdict"
          data-verdict={r.verdict}
        >
          <p className="text-lg font-semibold">{t(`offer.verdicts.${r.verdict}`)}</p>
          <p className="text-sm">{t(`offer.verdictText.${r.verdict}`)}</p>
          <ul className="mt-1 list-disc pl-5 text-sm">
            {r.flags.map((f) => (
              <li key={f}>{t(`offer.flags.${f}`)}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-2 text-xs opacity-70">{t('offer.rule')}</p>
    </section>
  );
}

export function CraftsPage() {
  const { t } = useTranslation();
  const ideas = useQuery({
    queryKey: ['crafts'],
    queryFn: () => unwrap(commands.listCraftIdeas()),
  });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('nav.crafts')}</h1>
      <p className="text-sm opacity-80">{t('craft.intro')}</p>
      <section className="rounded-lg border border-line p-5">
        <h2 className="font-semibold">{t('craft.newTitle')}</h2>
        <IdeaForm />
        <ul className="mt-3 divide-y divide-line">
          {ideas.data?.map((i) => (
            <IdeaCard key={i.id} i={i} />
          ))}
        </ul>
      </section>
      <OfferCheck />
    </div>
  );
}
