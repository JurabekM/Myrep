import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState, type FocusEvent, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto, type PartnershipInput } from '../../bindings';
import { errorMessage, percentToBp, unwrap } from '../../lib/api';

const ROLES_MUDARABA = ['CAPITAL_PROVIDER', 'WORKER'] as const;

/** 9 savol (SPEC 2F.2): har biri uchun qadam nomi va Sobir hoji maslahati kaliti. */
const QUESTIONS = [
  { step: 1, label: 'partner.steps.1', advice: 'partner.advice.1' },
  { step: 2, label: 'partner.steps.2', advice: 'partner.advice.2' },
  { step: 3, label: 'partner.steps.3', advice: 'partner.advice.3' },
  { step: 4, label: 'partner.steps.4', advice: 'partner.advice.4' },
  { step: 5, label: 'partner.steps.5', advice: 'partner.advice.5' },
  { step: 6, label: 'partner.steps.6', advice: 'partner.advice.6' },
  { step: 7, label: 'partner.steps.7', advice: 'partner.advice.7' },
  { step: 8, label: 'partner.steps.8', advice: 'partner.advice.8' },
  { step: 9, label: 'partner.steps.9', advice: 'partner.advice.9' },
] as const;

type StepState = 'done' | 'todo' | 'wrong' | 'pending';

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

/** Jonli önizleme PDF baytlarini brauzer blob-URL'iga aylantiradi (ma'lumot bo'lmasa `null`). */
function usePdfUrl(bytes: number[] | null): string | null {
  const url = useMemo(() => {
    if (bytes === null || typeof URL.createObjectURL !== 'function') return null;
    return URL.createObjectURL(new Blob([Uint8Array.from(bytes)], { type: 'application/pdf' }));
  }, [bytes]);
  useEffect(() => {
    return () => {
      if (url !== null) URL.revokeObjectURL(url);
    };
  }, [url]);
  return url;
}

/**
 * Shartnoma ustasi (SPEC 2E.2, 2F.2): chap tomonda 9 qadamli progress, o'rtada forma, o'ngda Sobir hoji
 * maslahati va shartnoma PDF'ining jonli önizlemesi. Tomon, kapital, vazifa va boshqa maydonlar
 * `data-step` bilan qaysi savolga tegishli ekani ko'rsatilgan. `existing` berilsa — o'zgartirish
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
  const formRef = useRef<HTMLFormElement>(null);
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
  const [activeStep, setActiveStep] = useState(1);

  const save = useMutation({
    mutationFn: (value: PartnershipInput) =>
      existing
        ? unwrap(commands.revisePartnership(existing.id, value))
        : unwrap(commands.createPartnership(value)),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      onDone();
    },
  });

  const update = (i: number, patch: Partial<PartyRow>) => {
    setParties((p) => p.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  };
  const roles: readonly string[] = kind === 'MUDARABA' ? ROLES_MUDARABA : ['PARTNER'];
  const defaultRole = roles[0] ?? 'PARTNER';

  // Forma qiymati: noto'g'ri ulush bo'lsa `null`. Har o'zgarishda yangi obyekt emas — faqat maydon o'zgarganda.
  const draftInput = useMemo<PartnershipInput | null>(() => {
    const rows: PartnershipInput['parties'] = [];
    const rolesNow: readonly string[] = kind === 'MUDARABA' ? ROLES_MUDARABA : ['PARTNER'];
    for (const p of parties) {
      const bp = percentToBp(p.share);
      if (bp === null) return null;
      rows.push({
        name: p.name,
        role: rolesNow.includes(p.role) ? p.role : (rolesNow[0] ?? 'PARTNER'),
        share_bp: bp,
        member_id: p.memberId === '' ? null : p.memberId,
        capital: p.capital,
        fixed_return: p.fixedReturn.trim() === '' ? null : p.fixedReturn,
      });
    }
    return {
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
    };
  }, [
    name,
    kind,
    term,
    period,
    endClause,
    dispute,
    witnesses,
    parties,
    duties,
    custodyPlace,
    arbiterName,
    reviewDate,
  ]);

  // Önizleme so'rovi yozishni kutib turadi: tez-tez tahrirda serverga har harfda so'rov ketmasin.
  const [debounced, setDebounced] = useState<PartnershipInput | null>(draftInput);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(draftInput);
    }, 350);
    return () => {
      window.clearTimeout(timer);
    };
  }, [draftInput]);

  const draft = useQuery({
    queryKey: ['partnership-draft', debounced],
    queryFn: () => unwrap(commands.checkPartnershipDraft(debounced as PartnershipInput)),
    enabled: debounced !== null,
    placeholderData: keepPreviousData,
  });
  const report = draft.data;
  const pdfUrl = usePdfUrl(report?.pdf ?? null);

  const stepState = (n: number): StepState => {
    if (!report) return 'pending';
    if (report.missing_questions.includes(n)) return 'todo';
    if (report.errors.some((e) => e.question === n)) return 'wrong';
    return 'done';
  };
  const doneCount = QUESTIONS.filter((q) => stepState(q.step) === 'done').length;

  const trackFocus = (e: FocusEvent<HTMLFormElement>) => {
    const n = Number((e.target as HTMLElement).closest<HTMLElement>('[data-step]')?.dataset.step);
    if (Number.isInteger(n) && n >= 1 && n <= 9) setActiveStep(n);
  };

  const jumpTo = (n: number) => {
    setActiveStep(n);
    const el = formRef.current?.querySelector<HTMLElement>(`[data-step="${String(n)}"]`);
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (draftInput === null) {
      setLocalError(t('partner.badPercent'));
      return;
    }
    save.mutate(draftInput);
  };

  const field = 'mt-1 block w-full rounded border border-line-strong bg-transparent p-1';
  const activeAdvice = (QUESTIONS[activeStep - 1] ?? QUESTIONS[0]).advice;
  return (
    <form
      ref={formRef}
      className="space-y-3 rounded-lg border border-accent p-5"
      onSubmit={submit}
      onFocus={trackFocus}
      data-testid="contract-form"
    >
      <h3 className="font-semibold">
        {existing ? t('partner.reviseTitle') : t('partner.newTitle')}
      </h3>
      {existing && <p className="text-sm">{t('partner.reviseHint')}</p>}
      <p className="text-sm opacity-80">{t('partner.principle')}</p>
      <div className="grid gap-4 lg:grid-cols-[12rem_minmax(0,1fr)_minmax(0,20rem)]">
        <aside className="space-y-2 lg:sticky lg:top-2 lg:self-start" data-testid="wizard-progress">
          <p className="text-sm font-semibold" data-testid="wizard-count">
            {t('partner.wizard.progress', { n: doneCount })}
          </p>
          <ol className="space-y-1">
            {QUESTIONS.map((q) => {
              const st = stepState(q.step);
              return (
                <li key={q.step} data-testid={`wizard-step-${String(q.step)}`} data-state={st}>
                  <button
                    type="button"
                    className={`flex w-full items-start gap-2 rounded p-1 text-left text-sm ${
                      activeStep === q.step ? 'bg-accent/10' : ''
                    }`}
                    onClick={() => {
                      jumpTo(q.step);
                    }}
                  >
                    <span aria-hidden="true" className="w-4 shrink-0">
                      {st === 'done' ? '✓' : st === 'pending' ? '·' : '!'}
                    </span>
                    <span>
                      {String(q.step)}. {t(q.label)}
                    </span>
                    <span className="sr-only">{t(`partner.wizard.${st}`)}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </aside>

        <div className="min-w-0 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm" data-step="1">
              {t('partner.name')}
              <input
                className={field}
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                }}
              />
            </label>
            <label className="block text-sm" data-step="1">
              {t('partner.kind')}
              <select
                className={field}
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
            <label className="block text-sm" data-step="9">
              {t('partner.term')}
              <input
                inputMode="numeric"
                className={field}
                value={term}
                onChange={(e) => {
                  setTerm(e.target.value);
                }}
              />
            </label>
            <label className="block text-sm" data-step="6">
              {t('partner.period')}
              <select
                className={field}
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
            <fieldset key={i} className="space-y-2 rounded border border-line p-3" data-step="1">
              <legend className="px-1 text-sm font-medium">
                {t('partner.partyN', { n: i + 1 })}
              </legend>
              <div className="grid gap-2 sm:grid-cols-4">
                <label className="block text-sm">
                  {t('partner.partyName', { n: i + 1 })}
                  <input
                    className={field}
                    value={p.name}
                    onChange={(e) => {
                      update(i, { name: e.target.value });
                    }}
                  />
                </label>
                <label className="block text-sm">
                  {t('partner.role', { n: i + 1 })}
                  <select
                    className={field}
                    value={roles.includes(p.role) ? p.role : defaultRole}
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
                <label className="block text-sm" data-step="4">
                  {t('partner.share', { n: i + 1 })}
                  <input
                    inputMode="decimal"
                    className={field}
                    value={p.share}
                    onChange={(e) => {
                      update(i, { share: e.target.value });
                    }}
                  />
                </label>
                <label className="block text-sm">
                  {t('partner.member', { n: i + 1 })}
                  <select
                    className={field}
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
              <div className="space-y-2" data-step="2">
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
                    update(i, {
                      capital: [...p.capital, { description: '', kind: 'CASH', value: '' }],
                    });
                  }}
                >
                  {t('partner.capAdd', { n: i + 1 })}
                </button>
                {p.role === 'CAPITAL_PROVIDER' && (
                  <label className="block text-sm">
                    {t('partner.fixedReturn')}
                    <input
                      inputMode="decimal"
                      className={field}
                      placeholder={t('partner.fixedReturnHint')}
                      value={p.fixedReturn}
                      onChange={(e) => {
                        update(i, { fixedReturn: e.target.value });
                      }}
                    />
                  </label>
                )}
              </div>
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
            <div className="space-y-2" data-step="3">
              {duties.map((d, i) => (
                <div
                  key={i}
                  className="grid gap-2 sm:grid-cols-[2fr_1fr_2fr_auto]"
                  data-testid={'duty-' + String(i)}
                >
                  <input
                    aria-label={t('partner.dutyText')}
                    className={field}
                    placeholder={t('partner.dutyText')}
                    value={d.text}
                    onChange={(e) => {
                      setDuties((x) =>
                        x.map((y, j) => (j === i ? { ...y, text: e.target.value } : y)),
                      );
                    }}
                  />
                  <select
                    aria-label={t('partner.dutyOwner')}
                    className={field}
                    value={d.owner}
                    onChange={(e) => {
                      setDuties((x) =>
                        x.map((y, j) => (j === i ? { ...y, owner: e.target.value } : y)),
                      );
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
                    className={field}
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
            </div>
            <label className="block text-sm" data-step="6">
              {t('partner.custodyPlace')}
              <input
                className={field}
                value={custodyPlace}
                onChange={(e) => {
                  setCustodyPlace(e.target.value);
                }}
              />
            </label>
            <label className="block text-sm" data-step="8">
              {t('partner.arbiterName')}
              <input
                className={field}
                value={arbiterName}
                onChange={(e) => {
                  setArbiterName(e.target.value);
                }}
              />
              <span className="text-xs opacity-70">{t('partner.arbiterHint')}</span>
            </label>
            <label className="block text-sm" data-step="9">
              {t('partner.reviewDate')}
              <input
                type="date"
                className={field}
                value={reviewDate}
                onChange={(e) => {
                  setReviewDate(e.target.value);
                }}
              />
              <span className="text-xs opacity-70">{t('partner.reviewHint')}</span>
            </label>
          </fieldset>

          <label className="block text-sm" data-step="7">
            {t('partner.endClause')}
            <textarea
              className={field}
              rows={2}
              value={endClause}
              onChange={(e) => {
                setEndClause(e.target.value);
              }}
            />
          </label>
          <label className="block text-sm" data-step="8">
            {t('partner.dispute')}
            <textarea
              className={field}
              rows={2}
              value={dispute}
              onChange={(e) => {
                setDispute(e.target.value);
              }}
            />
          </label>
          <label className="block text-sm" data-step="8">
            {t('partner.witnesses')}
            <input
              className={field}
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
        </div>

        <aside className="space-y-3 lg:sticky lg:top-2 lg:self-start" data-testid="wizard-side">
          <section className="rounded border border-line p-3 text-sm" data-testid="wizard-advice">
            <h4 className="font-semibold">{t('partner.adviceTitle')}</h4>
            <p className="mt-1">{t(activeAdvice)}</p>
          </section>
          <section className="rounded border border-line p-3" data-testid="draft-preview">
            <h4 className="mb-2 text-sm font-semibold">{t('partner.previewTitle')}</h4>
            {draftInput === null ? (
              <p className="text-sm opacity-80">{t('partner.badPercent')}</p>
            ) : pdfUrl !== null ? (
              <iframe
                title={t('partner.previewTitle')}
                src={pdfUrl}
                className="h-[32rem] w-full rounded border border-line"
              />
            ) : report?.pdf === null ? (
              <p className="text-sm opacity-80" data-testid="draft-preview-blocked">
                {t('partner.previewBlocked')}
              </p>
            ) : draft.isError ? (
              <p className="text-sm opacity-80">{errorMessage(t, draft.error)}</p>
            ) : (
              <p className="text-sm opacity-80">
                {draft.isFetching ? t('partner.previewLoading') : t('partner.previewWaiting')}
              </p>
            )}
          </section>
        </aside>
      </div>
    </form>
  );
}
