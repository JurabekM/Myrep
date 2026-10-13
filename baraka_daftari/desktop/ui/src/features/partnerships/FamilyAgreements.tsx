import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import {
  commands,
  type FamilyAgreementDto,
  type FamilyDutyInput,
  type MemberDto,
} from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

const TEMPLATES = ['HOUSE_DUTIES', 'HOUSE_MONEY', 'DESIRE_LIMIT', 'COUNCIL_SCHEDULE'] as const;
type TemplateCode = (typeof TEMPLATES)[number];

const field = 'mt-1 block w-full rounded border border-line-strong bg-transparent p-1';

/**
 * Oilaviy kelishuvlar (SPEC 2F.10, D13A): namunaviy shablondan qoralama, kattalarning PIN bilan tasdig'i
 * va faollashtirish. Imzo o'rniga har bir katta a'zoning tasdig'i yetarli; bolalar tasdiqlamaydi.
 */
export function FamilyAgreements() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [template, setTemplate] = useState<TemplateCode | null>(null);
  const members = useQuery({
    queryKey: ['members'],
    queryFn: () => unwrap(commands.listMembers()),
  });
  const list = useQuery({
    queryKey: ['family-agreements'],
    queryFn: () => unwrap(commands.familyAgreementsList()),
  });
  const adults = (members.data ?? []).filter((m) => m.role === 'ADULT');
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['family-agreements'] });
  };
  return (
    <section
      className="space-y-3 rounded-lg border border-line p-4"
      data-testid="family-agreements"
    >
      <h2 className="font-semibold">{t('famagr.title')}</h2>
      <p className="text-sm opacity-80">{t('famagr.intro')}</p>
      {template === null ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span>{t('famagr.new')}</span>
          {TEMPLATES.map((code) => (
            <button
              key={code}
              type="button"
              className="rounded border border-accent px-3 py-1"
              onClick={() => {
                setTemplate(code);
              }}
            >
              {t(`famagr.templates.${code}.title`)}
            </button>
          ))}
        </div>
      ) : (
        <FamilyForm
          template={template}
          adults={adults}
          onDone={() => {
            setTemplate(null);
            refresh();
          }}
          onCancel={() => {
            setTemplate(null);
          }}
        />
      )}
      {(list.data ?? []).length === 0 ? (
        <p className="text-sm opacity-70">{t('famagr.empty')}</p>
      ) : (
        (list.data ?? []).map((a) => <FamilyCard key={a.id} a={a} onChange={refresh} />)
      )}
    </section>
  );
}

function FamilyForm({
  template,
  adults,
  onDone,
  onCancel,
}: {
  template: TemplateCode;
  adults: MemberDto[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(() => t(`famagr.templates.${template}.title`));
  const [picked, setPicked] = useState<string[]>(() => adults.map((a) => a.id));
  const [duties, setDuties] = useState<FamilyDutyInput[]>(() => [
    {
      text: t(`famagr.templates.${template}.duty`),
      owner_member_id: adults[0]?.id ?? '',
      if_not_done: t(`famagr.templates.${template}.ifNotDone`),
    },
  ]);
  const [custody, setCustody] = useState('');
  const [review, setReview] = useState('');
  const create = useMutation({
    mutationFn: () =>
      unwrap(
        commands.createFamilyAgreement({
          title,
          adult_ids: picked,
          duties,
          custody_place: custody,
          review_date: review === '' ? null : review,
        }),
      ),
    onSuccess: onDone,
  });
  // Kattalardan biri chiqarilsa, uning vazifalari qolgan kattalarga o'tadi (mas'ul yagona bo'lsin).
  const togglePick = (id: string) => {
    const next = picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id];
    setPicked(next);
    const fallback = next[0] ?? '';
    setDuties(
      duties.map((d) =>
        next.includes(d.owner_member_id) ? d : { ...d, owner_member_id: fallback },
      ),
    );
  };
  const canSubmit =
    picked.length > 0 &&
    custody.trim() !== '' &&
    duties.length > 0 &&
    duties.every((d) => d.text.trim() !== '' && d.if_not_done.trim() !== '');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <form
      className="space-y-3 rounded border border-accent p-3"
      onSubmit={submit}
      data-testid="family-form"
    >
      <p className="font-medium">{t(`famagr.templates.${template}.title`)}</p>
      <p className="text-xs opacity-80">{t(`famagr.templates.${template}.hint`)}</p>
      <label className="block text-sm">
        {t('famagr.name')}
        <input
          className={field}
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
          }}
        />
      </label>
      <fieldset className="space-y-1 text-sm">
        <legend className="font-medium">{t('famagr.adults')}</legend>
        {adults.map((a) => (
          <label key={a.id} className="mr-3 inline-flex items-center gap-1">
            <input
              type="checkbox"
              checked={picked.includes(a.id)}
              onChange={() => {
                togglePick(a.id);
              }}
            />
            {a.name}
          </label>
        ))}
      </fieldset>
      <fieldset className="space-y-2 text-sm">
        <legend className="font-medium">{t('famagr.duties')}</legend>
        {duties.map((d, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[2fr_1fr_2fr_auto]">
            <input
              aria-label={t('famagr.dutyText')}
              className={field}
              value={d.text}
              onChange={(e) => {
                setDuties(duties.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)));
              }}
            />
            <select
              aria-label={t('famagr.dutyOwner')}
              className={field}
              value={d.owner_member_id}
              onChange={(e) => {
                setDuties(
                  duties.map((x, j) => (j === i ? { ...x, owner_member_id: e.target.value } : x)),
                );
              }}
            >
              {picked.map((id) => (
                <option key={id} value={id}>
                  {adults.find((a) => a.id === id)?.name ?? id}
                </option>
              ))}
            </select>
            <input
              aria-label={t('famagr.dutyIfNotDone')}
              className={field}
              value={d.if_not_done}
              onChange={(e) => {
                setDuties(
                  duties.map((x, j) => (j === i ? { ...x, if_not_done: e.target.value } : x)),
                );
              }}
            />
            <button
              type="button"
              className="underline"
              onClick={() => {
                setDuties(duties.filter((_, j) => j !== i));
              }}
            >
              {t('famagr.removeDuty')}
            </button>
          </div>
        ))}
        <button
          type="button"
          className="underline"
          onClick={() => {
            setDuties([...duties, { text: '', owner_member_id: picked[0] ?? '', if_not_done: '' }]);
          }}
        >
          {t('famagr.addDuty')}
        </button>
      </fieldset>
      <label className="block text-sm">
        {t('famagr.custody')}
        <input
          className={field}
          value={custody}
          onChange={(e) => {
            setCustody(e.target.value);
          }}
        />
      </label>
      <label className="block text-sm">
        {t('famagr.reviewDate')}
        <input
          type="date"
          className={field}
          value={review}
          onChange={(e) => {
            setReview(e.target.value);
          }}
        />
      </label>
      {create.error && <p role="alert">{errorMessage(t, create.error)}</p>}
      <div className="flex gap-3">
        <button
          type="submit"
          className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
          disabled={!canSubmit || create.isPending}
        >
          {t('famagr.create')}
        </button>
        <button type="button" className="text-sm underline" onClick={onCancel}>
          {t('debts.cancel')}
        </button>
      </div>
    </form>
  );
}

function FamilyCard({ a, onChange }: { a: FamilyAgreementDto; onChange: () => void }) {
  const { t } = useTranslation();
  const [pins, setPins] = useState<Record<string, string>>({});
  const sign = useMutation({
    mutationFn: (v: { memberId: string; pin: string }) =>
      unwrap(commands.signFamilyAgreement(a.id, v.memberId, v.pin)),
    onSuccess: (_data, v) => {
      setPins((x) => ({ ...x, [v.memberId]: '' }));
      onChange();
    },
  });
  const activate = useMutation({
    mutationFn: () => unwrap(commands.activateFamilyAgreement(a.id)),
    onSuccess: onChange,
  });
  const error = [sign.error, activate.error].find((x) => x !== null);
  return (
    <article className="space-y-2 rounded border border-line p-3 text-sm" data-testid="famagr-card">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">{a.title}</h3>
        <span
          className="rounded border border-line-strong px-2 text-xs"
          data-testid="famagr-status"
        >
          {t(`famagr.statuses.${a.status}`)} · v{String(a.version)}
        </span>
      </div>
      {a.review_date && (
        <p className="text-xs opacity-80">{t('famagr.review', { date: a.review_date })}</p>
      )}
      <p className="text-xs opacity-80">{a.custody_place}</p>
      <ul className="space-y-1">
        {a.duties.map((d, i) => (
          <li key={i}>{`${d.text} · ${d.owner_name} · ${d.if_not_done}`}</li>
        ))}
      </ul>
      <ul className="space-y-2">
        {a.adults.map((x) => (
          <li
            key={x.member_id}
            className="flex flex-wrap items-center justify-between gap-2"
            data-testid={`famagr-adult-${x.name}`}
          >
            <span>{x.name}</span>
            {x.signed ? (
              <span role="status">{`✓ ${t('famagr.signedBy')}`}</span>
            ) : a.status === 'DRAFT' ? (
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  sign.mutate({ memberId: x.member_id, pin: pins[x.member_id] ?? '' });
                }}
              >
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={6}
                  aria-label={t('famagr.pinFor', { name: x.name })}
                  className="w-24 rounded border border-line-strong bg-transparent p-1"
                  value={pins[x.member_id] ?? ''}
                  onChange={(e) => {
                    setPins((p) => ({ ...p, [x.member_id]: e.target.value }));
                  }}
                />
                <button
                  type="submit"
                  className="rounded border border-accent px-2 py-0.5 disabled:opacity-50"
                  disabled={(pins[x.member_id] ?? '') === '' || sign.isPending}
                >
                  {t('famagr.confirm')}
                </button>
              </form>
            ) : null}
          </li>
        ))}
      </ul>
      {a.can_activate && (
        <button
          type="button"
          className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
          disabled={activate.isPending}
          onClick={() => {
            activate.mutate();
          }}
        >
          {t('famagr.activate')}
        </button>
      )}
      {error && <p role="alert">{errorMessage(t, error)}</p>}
    </article>
  );
}
