import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto, type PartnershipInput } from '../../bindings';
import { errorMessage, percentToBp, unwrap } from '../../lib/api';

const ROLES_MUDARABA = ['CAPITAL_PROVIDER', 'WORKER'] as const;

interface CapitalRow {
  description: string;
  kind: 'CASH' | 'EQUIPMENT';
  value: string;
}

interface DutyRow {
  text: string;
  owner: string;
  ifNotDone: string;
}

interface PartyRow {
  name: string;
  role: string;
  share: string;
  memberId: string;
  fixedReturn: string;
  capital: CapitalRow[];
}

function fromDto(p: PartnershipDto): PartyRow[] {
  return p.parties.map((x) => ({
    name: x.name,
    role: x.role,
    share: String(x.share_bp / 100).replace('.', ','),
    memberId: x.member_id ?? '',
    fixedReturn: '',
    capital: x.items.map((i) => ({
      description: i.description,
      kind: i.kind as 'CASH' | 'EQUIPMENT',
      value: i.value_text,
    })),
  }));
}

/**
 * Shartnoma ustasi (SPEC 2E.2): tur, tomonlar va ularning kapitali (pul va uskunalar narxi bilan),
 * foyda ulushlari, muddat, hisobot, tugash va nizo tartibi, guvohlar. `existing` berilsa — o'zgartirish
 * (yangi versiya; barcha tasdiqlar qayta so'raladi).
 */
export function ContractForm({
  existing,
  onDone,
}: {
  existing?: PartnershipDto;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const members = useQuery({
    queryKey: ['members'],
    queryFn: () => unwrap(commands.listMembers()),
  });
  const [name, setName] = useState(existing?.name ?? '');
  const [kind, setKind] = useState<'MUDARABA' | 'MUSHARAKA'>(
    (existing?.kind as 'MUDARABA' | 'MUSHARAKA' | undefined) ?? 'MUDARABA',
  );
  const [term, setTerm] = useState(String(existing?.term_months ?? 12));
  const [period, setPeriod] = useState(existing?.report_period ?? 'MONTHLY');
  const [endClause, setEndClause] = useState(existing?.end_clause ?? '');
  const [dispute, setDispute] = useState(existing?.dispute_clause ?? '');
  const [witnesses, setWitnesses] = useState(
    existing?.witnesses.map((w) => w.name).join(', ') ?? '',
  );
  const [parties, setParties] = useState<PartyRow[]>(
    existing
      ? fromDto(existing)
      : [
          {
            name: '',
            role: 'CAPITAL_PROVIDER',
            share: '50',
            memberId: '',
            fixedReturn: '',
            capital: [],
          },
          { name: '', role: 'WORKER', share: '50', memberId: '', fixedReturn: '', capital: [] },
        ],
  );
  const [duties, setDuties] = useState<DutyRow[]>(
    existing?.agreement?.duties.map((d) => ({
      text: d.text,
      owner: d.owner_name,
      ifNotDone: d.if_not_done,
    })) ?? [],
  );
  const [custodyPlace, setCustodyPlace] = useState(existing?.agreement?.custody_place ?? '');
  const [arbiterName, setArbiterName] = useState(existing?.agreement?.arbiter_name ?? '');
  const [reviewDate, setReviewDate] = useState(existing?.agreement?.review_date ?? '');
  const [localError, setLocalError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (input: PartnershipInput) =>
      existing
        ? unwrap(commands.revisePartnership(existing.id, input))
        : unwrap(commands.createPartnership(input)),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      onDone();
    },
  });

  const update = (i: number, patch: Partial<PartyRow>) => {
    setParties((p) => p.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  };
  const roles = kind === 'MUDARABA' ? ROLES_MUDARABA : (['PARTNER'] as const);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    const rows = [];
    for (const p of parties) {
      const bp = percentToBp(p.share);
      if (bp === null) {
        setLocalError(t('partner.badPercent'));
        return;
      }
      rows.push({
        name: p.name,
        role: roles.includes(p.role as never) ? p.role : roles[0],
        share_bp: bp,
        member_id: p.memberId === '' ? null : p.memberId,
        capital: p.capital,
        fixed_return: p.fixedReturn.trim() === '' ? null : p.fixedReturn,
      });
    }
    save.mutate({
      name,
      kind,
      term_months: Number.parseInt(term, 10) || 0,
      report_period: period,
      end_clause: endClause,
      dispute_clause: dispute,
      witnesses: witnesses
        .split(/[,\n]/)
        .map((w) => w.trim())
        .filter((w) => w !== ''),
      parties: rows,
      duties: duties
        .filter((d) => d.text.trim() !== '')
        .map((d) => ({ text: d.text, owner_name: d.owner, if_not_done: d.ifNotDone })),
      custody_place: custodyPlace,
      arbiter_name: arbiterName,
      review_date: reviewDate === '' ? null : reviewDate,
    });
  };

  const input = 'mt-1 block w-full rounded border border-line-strong bg-transparent p-1';
  return (
    <form
      className="space-y-3 rounded-lg border border-accent p-5"
      onSubmit={submit}
      data-testid="contract-form"
    >
      <h3 className="font-semibold">
        {existing ? t('partner.reviseTitle') : t('partner.newTitle')}
      </h3>
      {existing && <p className="text-sm">{t('partner.reviseHint')}</p>}
      <p className="text-sm opacity-80">{t('partner.principle')}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          {t('partner.name')}
          <input
            className={input}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('partner.kind')}
          <select
            className={input}
            value={kind}
            onChange={(e) => {
              const k = e.target.value as 'MUDARABA' | 'MUSHARAKA';
              setKind(k);
              setParties((p) =>
                p.map((x) => ({
                  ...x,
                  role:
                    k === 'MUSHARAKA'
                      ? 'PARTNER'
                      : x.role === 'WORKER'
                        ? 'WORKER'
                        : 'CAPITAL_PROVIDER',
                })),
              );
            }}
          >
            <option value="MUDARABA">{t('partner.kinds.MUDARABA')}</option>
            <option value="MUSHARAKA">{t('partner.kinds.MUSHARAKA')}</option>
          </select>
        </label>
        <label className="block text-sm">
          {t('partner.term')}
          <input
            inputMode="numeric"
            className={input}
            value={term}
            onChange={(e) => {
              setTerm(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('partner.period')}
          <select
            className={input}
            value={period}
            onChange={(e) => {
              setPeriod(e.target.value);
            }}
          >
            {(['MONTHLY', 'QUARTERLY', 'YEARLY'] as const).map((p) => (
              <option key={p} value={p}>
                {t(`partner.periods.${p}`)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {parties.map((p, i) => (
        <fieldset key={i} className="space-y-2 rounded border border-line p-3">
          <legend className="px-1 text-sm font-medium">{t('partner.partyN', { n: i + 1 })}</legend>
          <div className="grid gap-2 sm:grid-cols-4">
            <label className="block text-sm">
              {t('partner.partyName', { n: i + 1 })}
              <input
                className={input}
                value={p.name}
                onChange={(e) => {
                  update(i, { name: e.target.value });
                }}
              />
            </label>
            <label className="block text-sm">
              {t('partner.role', { n: i + 1 })}
              <select
                className={input}
                value={roles.includes(p.role as never) ? p.role : roles[0]}
                onChange={(e) => {
                  update(i, { role: e.target.value });
                }}
              >
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {t(`partner.roles.${r}`)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              {t('partner.share', { n: i + 1 })}
              <input
                inputMode="decimal"
                className={input}
                value={p.share}
                onChange={(e) => {
                  update(i, { share: e.target.value });
                }}
              />
            </label>
            <label className="block text-sm">
              {t('partner.member', { n: i + 1 })}
              <select
                className={input}
                value={p.memberId}
                onChange={(e) => {
                  update(i, { memberId: e.target.value });
                }}
              >
                <option value="">{t('partner.external')}</option>
                {members.data?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {p.capital.map((c, k) => (
            <div key={k} className="flex flex-wrap gap-2">
              <input
                aria-label={t('partner.capDesc', { n: i + 1, k: k + 1 })}
                placeholder={t('partner.capDescPh')}
                className="flex-1 rounded border border-line-strong bg-transparent p-1"
                value={c.description}
                onChange={(e) => {
                  update(i, {
                    capital: p.capital.map((x, j) =>
                      j === k ? { ...x, description: e.target.value } : x,
                    ),
                  });
                }}
              />
              <select
                aria-label={t('partner.capKind', { n: i + 1, k: k + 1 })}
                className="rounded border border-line-strong bg-transparent p-1"
                value={c.kind}
                onChange={(e) => {
                  update(i, {
                    capital: p.capital.map((x, j) =>
                      j === k ? { ...x, kind: e.target.value as 'CASH' | 'EQUIPMENT' } : x,
                    ),
                  });
                }}
              >
                <option value="CASH">{t('partner.capKinds.CASH')}</option>
                <option value="EQUIPMENT">{t('partner.capKinds.EQUIPMENT')}</option>
              </select>
              <input
                aria-label={t('partner.capValue', { n: i + 1, k: k + 1 })}
                inputMode="decimal"
                placeholder={t('partner.capValuePh')}
                className="w-36 rounded border border-line-strong bg-transparent p-1"
                value={c.value}
                onChange={(e) => {
                  update(i, {
                    capital: p.capital.map((x, j) =>
                      j === k ? { ...x, value: e.target.value } : x,
                    ),
                  });
                }}
              />
              <button
                type="button"
                className="text-sm underline"
                onClick={() => {
                  update(i, { capital: p.capital.filter((_, j) => j !== k) });
                }}
              >
                {t('partner.capRemove')}
              </button>
            </div>
          ))}
          <button
            type="button"
            className="text-sm underline"
            onClick={() => {
              update(i, { capital: [...p.capital, { description: '', kind: 'CASH', value: '' }] });
            }}
          >
            {t('partner.capAdd', { n: i + 1 })}
          </button>
          {p.role === 'CAPITAL_PROVIDER' && (
            <label className="block text-sm">
              {t('partner.fixedReturn')}
              <input
                inputMode="decimal"
                className={input}
                placeholder={t('partner.fixedReturnHint')}
                value={p.fixedReturn}
                onChange={(e) => {
                  update(i, { fixedReturn: e.target.value });
                }}
              />
            </label>
          )}
        </fieldset>
      ))}
      {parties.length < 6 && (
        <button
          type="button"
          className="text-sm underline"
          onClick={() => {
            setParties((p) => [
              ...p,
              {
                name: '',
                role: roles[roles.length - 1] ?? 'PARTNER',
                share: '0',
                memberId: '',
                fixedReturn: '',
                capital: [],
              },
            ]);
          }}
        >
          {t('partner.addParty')}
        </button>
      )}

      <fieldset
        className="space-y-2 rounded border border-line p-3"
        data-testid="agreement-questions"
      >
        <legend className="px-1 text-sm font-semibold">{t('partner.questionsTitle')}</legend>
        <p className="text-xs opacity-70">{t('partner.questionsHint')}</p>
        {duties.map((d, i) => (
          <div
            key={i}
            className="grid gap-2 sm:grid-cols-[2fr_1fr_2fr_auto]"
            data-testid={'duty-' + String(i)}
          >
            <input
              aria-label={t('partner.dutyText')}
              className={input}
              placeholder={t('partner.dutyText')}
              value={d.text}
              onChange={(e) => {
                setDuties((x) => x.map((y, j) => (j === i ? { ...y, text: e.target.value } : y)));
              }}
            />
            <select
              aria-label={t('partner.dutyOwner')}
              className={input}
              value={d.owner}
              onChange={(e) => {
                setDuties((x) => x.map((y, j) => (j === i ? { ...y, owner: e.target.value } : y)));
              }}
            >
              <option value="">{t('partner.dutyOwnerPick')}</option>
              {parties
                .filter((p) => p.name.trim() !== '')
                .map((p) => (
                  <option key={p.name} value={p.name.trim()}>
                    {p.name.trim()}
                  </option>
                ))}
            </select>
            <input
              aria-label={t('partner.dutyIfNotDone')}
              className={input}
              placeholder={t('partner.dutyIfNotDone')}
              value={d.ifNotDone}
              onChange={(e) => {
                setDuties((x) =>
                  x.map((y, j) => (j === i ? { ...y, ifNotDone: e.target.value } : y)),
                );
              }}
            />
            <button
              type="button"
              className="text-sm underline"
              onClick={() => {
                setDuties((x) => x.filter((_, j) => j !== i));
              }}
            >
              {t('partner.removeDuty')}
            </button>
          </div>
        ))}
        <button
          type="button"
          className="text-sm underline"
          onClick={() => {
            setDuties((x) => [...x, { text: '', owner: '', ifNotDone: '' }]);
          }}
        >
          {t('partner.addDuty')}
        </button>
        <label className="block text-sm">
          {t('partner.custodyPlace')}
          <input
            className={input}
            value={custodyPlace}
            onChange={(e) => {
              setCustodyPlace(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          {t('partner.arbiterName')}
          <input
            className={input}
            value={arbiterName}
            onChange={(e) => {
              setArbiterName(e.target.value);
            }}
          />
          <span className="text-xs opacity-70">{t('partner.arbiterHint')}</span>
        </label>
        <label className="block text-sm">
          {t('partner.reviewDate')}
          <input
            type="date"
            className={input}
            value={reviewDate}
            onChange={(e) => {
              setReviewDate(e.target.value);
            }}
          />
          <span className="text-xs opacity-70">{t('partner.reviewHint')}</span>
        </label>
      </fieldset>

      <label className="block text-sm">
        {t('partner.endClause')}
        <textarea
          className={input}
          rows={2}
          value={endClause}
          onChange={(e) => {
            setEndClause(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('partner.dispute')}
        <textarea
          className={input}
          rows={2}
          value={dispute}
          onChange={(e) => {
            setDispute(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('partner.witnesses')}
        <input
          className={input}
          value={witnesses}
          onChange={(e) => {
            setWitnesses(e.target.value);
          }}
        />
      </label>
      <p className="text-xs opacity-70">{t('partner.regulatory')}</p>
      {(localError ?? save.error) ? (
        <p role="alert" className="text-sm font-semibold" data-testid="form-error">
          {localError ?? errorMessage(t, save.error)}
        </p>
      ) : null}
      <div className="flex gap-3">
        <button
          type="submit"
          className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
          disabled={save.isPending}
        >
          {t('partner.saveContract')}
        </button>
        <button type="button" className="text-sm underline" onClick={onDone}>
          {t('debts.cancel')}
        </button>
      </div>
    </form>
  );
}
