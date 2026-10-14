import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type ForkDto, type ImportReportDto, type JournalSideDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

const inp = 'mt-1 block w-64 rounded border border-line-strong bg-transparent p-1';

function ExportSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: ['exchange-status'],
    queryFn: () => unwrap(commands.exchangeStatus()),
  });
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [incremental, setIncremental] = useState(false);
  const [withAttachments, setWithAttachments] = useState(true);
  const [saved, setSaved] = useState<string | null>(null);
  const last = status.data?.last_export ?? null;
  const exp = useMutation({
    mutationFn: () =>
      unwrap(commands.exportBaraka(pw, incremental && last !== null, withAttachments)),
    onSuccess: async (name) => {
      if (name !== null) {
        setSaved(name);
        setPw('');
        setPw2('');
      }
      await queryClient.invalidateQueries({ queryKey: ['exchange-status'] });
    },
  });
  const mismatch = pw2 !== '' && pw !== pw2;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (pw !== '' && pw === pw2) exp.mutate();
  };
  return (
    <section className="rounded-lg border border-line p-5">
      <h2 className="font-semibold">{t('exchange.exportTitle')}</h2>
      <form onSubmit={submit} className="mt-2 space-y-2 text-sm">
        <label className="block">
          {t('exchange.password')}
          <input
            type="password"
            autoComplete="new-password"
            className={inp}
            value={pw}
            onChange={(e) => {
              setPw(e.target.value);
            }}
          />
        </label>
        <label className="block">
          {t('exchange.passwordConfirm')}
          <input
            type="password"
            autoComplete="new-password"
            className={inp}
            value={pw2}
            onChange={(e) => {
              setPw2(e.target.value);
            }}
          />
        </label>
        <p className="text-xs opacity-70">{t('exchange.passwordHint')}</p>
        {mismatch && (
          <p role="alert" className="text-sm">
            {t('exchange.mismatch')}
          </p>
        )}
        <fieldset className="space-y-1">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={!incremental}
              onChange={() => {
                setIncremental(false);
              }}
            />
            {t('exchange.full')}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              disabled={last === null}
              checked={incremental}
              onChange={() => {
                setIncremental(true);
              }}
            />
            {t('exchange.incremental')}
          </label>
        </fieldset>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={withAttachments}
            onChange={(e) => {
              setWithAttachments(e.target.checked);
            }}
          />
          {t('exchange.withAttachments')}
        </label>
        <p className="text-xs opacity-70">{t('exchange.attachmentsHint')}</p>
        <p className="text-xs opacity-70">
          {last === null ? t('exchange.noExport') : t('exchange.lastExport', { when: last })}
        </p>
        <button
          type="submit"
          className="rounded bg-accent px-3 py-1 text-paper"
          disabled={pw === '' || mismatch || pw2 === ''}
        >
          {t('exchange.export')}
        </button>
      </form>
      {saved !== null && (
        <p role="status" className="mt-2 text-sm">
          {t('exchange.exported', { name: saved })}
        </p>
      )}
      {exp.error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, exp.error)}
        </p>
      ) : null}
    </section>
  );
}

function Report({ r }: { r: ImportReportDto }) {
  const { t } = useTranslation();
  return (
    <div className="mt-3 space-y-2 text-sm" data-testid="import-report">
      <h3 className="font-medium">{t('exchange.reportTitle')}</h3>
      <p>
        {t('exchange.summary', {
          inserted: r.inserted,
          updated: r.updated,
          unchanged: r.unchanged,
          kept: r.kept_local,
        })}
      </p>
      {r.adults_without_pin.length > 0 && (
        <p role="note" data-testid="needs-pin" className="rounded border border-line-strong p-2">
          {t('exchange.needsPin', { names: r.adults_without_pin.join(', ') })}
        </p>
      )}
      {r.conflicts.length === 0 ? (
        <p>{t('exchange.noConflicts')}</p>
      ) : (
        <>
          <h4 className="font-medium">{t('exchange.conflictsTitle', { n: r.conflicts.length })}</h4>
          <ul className="divide-y divide-line">
            {r.conflicts.map((c) => (
              <li key={`${c.table}-${c.id}`} className="py-1" data-testid={`conflict-${c.kind}`}>
                <strong>{c.label}</strong> — {t(`exchange.kinds.${c.kind}`)} (
                {t(`exchange.resolutions.${c.resolution}`)})
              </li>
            ))}
          </ul>
        </>
      )}
      {r.forks.length > 0 && <ForkPanel forks={r.forks} />}
    </div>
  );
}

const area = 'mt-1 block w-full rounded border border-line-strong bg-transparent p-1';

/**
 * Ayrilib ketgan kelishuv jurnali (fork): ikki nusxa tafsiloti. Import to'xtatilgan, hech narsa yozilmagan;
 * tomon nizo ochishi mumkin — nizo taqsimotni bloklaydi va hakam qaror beradi (SPEC 2F.6, 2F.8).
 */
function ForkPanel({ forks }: { forks: ForkDto[] }) {
  const { t } = useTranslation();
  return (
    <section className="space-y-3 rounded border border-line-strong p-3" data-testid="fork-panel">
      <h4 className="font-medium">{t('exchange.fork.heading')}</h4>
      <p className="text-xs opacity-80">{t('exchange.fork.explain')}</p>
      {forks.map((f) => (
        <ForkCard key={f.agreement_id} fork={f} />
      ))}
    </section>
  );
}

function SideBox({ title, side }: { title: string; side: JournalSideDto }) {
  const { t } = useTranslation();
  return (
    <div className="rounded border border-line p-2">
      <p className="font-medium">{title}</p>
      <p>
        {side.count === 0
          ? t('exchange.fork.none')
          : t('exchange.fork.entries', {
              n: side.count,
              first: side.first_seq,
              last: side.last_seq,
            })}
      </p>
      {side.count > 0 && (
        <p className="text-xs opacity-80">
          {t('exchange.fork.lastEntry', { date: side.last_date, note: side.last_note })}
        </p>
      )}
      <p className="break-all font-mono text-xs opacity-70">
        {side.head === '' ? '—' : side.head.slice(0, 16)}
      </p>
    </div>
  );
}

function ForkCard({ fork }: { fork: ForkDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [claimant, setClaimant] = useState(fork.parties[0]?.id ?? '');
  const [subject, setSubject] = useState(() => t('exchange.fork.subject'));
  const [claim, setClaim] = useState(() =>
    t('exchange.fork.claimTemplate', {
      local: fork.local.count,
      incoming: fork.incoming.count,
      seq: fork.diverged_seq,
    }),
  );
  const dispute = useMutation({
    mutationFn: () =>
      unwrap(
        commands.openAgreementDispute(fork.agreement_id, claimant, subject.trim(), claim.trim()),
      ),
    onSuccess: async () => {
      setOpen(false);
      await queryClient.invalidateQueries();
    },
  });
  const canSubmit =
    claimant !== '' && subject.trim() !== '' && claim.trim() !== '' && !dispute.isPending;
  return (
    <article
      className="space-y-2 rounded border border-line p-2"
      data-testid={`fork-${fork.agreement_id}`}
    >
      <p className="font-medium">{fork.title || fork.agreement_id}</p>
      <p>{t('exchange.fork.diverged', { seq: fork.diverged_seq })}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <SideBox title={t('exchange.fork.local')} side={fork.local} />
        <SideBox title={t('exchange.fork.incoming')} side={fork.incoming} />
      </div>
      {dispute.isSuccess ? (
        <p role="status">{t('exchange.fork.opened')}</p>
      ) : open ? (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            dispute.mutate();
          }}
        >
          <label className="block">
            {t('exchange.fork.claimant')}
            <select
              className={inp}
              value={claimant}
              onChange={(e) => {
                setClaimant(e.target.value);
              }}
            >
              {fork.parties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            {t('exchange.fork.subjectLabel')}
            <input
              className={inp}
              maxLength={80}
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
              }}
            />
          </label>
          <label className="block">
            {t('exchange.fork.claimLabel')}
            <textarea
              className={area}
              maxLength={300}
              rows={3}
              value={claim}
              onChange={(e) => {
                setClaim(e.target.value);
              }}
            />
          </label>
          <div className="flex gap-3">
            <button
              type="submit"
              className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
              disabled={!canSubmit}
            >
              {t('exchange.fork.submit')}
            </button>
            <button
              type="button"
              className="text-sm underline"
              onClick={() => {
                setOpen(false);
              }}
            >
              {t('debts.cancel')}
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
            disabled={fork.parties.length === 0}
            onClick={() => {
              setOpen(true);
            }}
          >
            {t('exchange.fork.openDispute')}
          </button>
          <p className="text-xs opacity-80">{t('exchange.fork.keepHint')}</p>
        </div>
      )}
      {dispute.error && <p role="alert">{errorMessage(t, dispute.error)}</p>}
    </article>
  );
}

function ImportSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState<string | null>(null);
  const [pw, setPw] = useState('');
  const [report, setReport] = useState<ImportReportDto | null>(null);
  const [done, setDone] = useState(false);
  const pick = useMutation({
    mutationFn: () => unwrap(commands.importBarakaPick()),
    onSuccess: (n) => {
      if (n !== null) {
        setName(n);
        setReport(null);
        setDone(false);
      }
    },
  });
  const preview = useMutation({
    mutationFn: () => unwrap(commands.importBarakaPreview(pw)),
    onSuccess: setReport,
  });
  const apply = useMutation({
    mutationFn: () => unwrap(commands.importBarakaApply(pw)),
    onSuccess: async (r) => {
      setReport(r);
      setDone(true);
      setName(null);
      setPw('');
      await queryClient.invalidateQueries();
    },
  });
  const cancel = useMutation({
    mutationFn: () => commands.importBarakaCancel(),
    onSuccess: () => {
      setName(null);
      setReport(null);
      setPw('');
    },
  });
  const error = pick.error ?? preview.error ?? apply.error;
  return (
    <section className="rounded-lg border border-line p-5">
      <h2 className="font-semibold">{t('exchange.importTitle')}</h2>
      <div className="mt-2 space-y-2 text-sm">
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          onClick={() => {
            pick.mutate();
          }}
        >
          {t('exchange.pick')}
        </button>
        {name !== null && (
          <>
            <p>{t('exchange.picked', { name })}</p>
            <label className="block">
              {t('exchange.importPassword')}
              <input
                type="password"
                autoComplete="off"
                className={inp}
                value={pw}
                onChange={(e) => {
                  setPw(e.target.value);
                  setReport(null);
                }}
              />
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded border border-accent px-3 py-1"
                disabled={pw === ''}
                onClick={() => {
                  preview.mutate();
                }}
              >
                {t('exchange.check')}
              </button>
              <button
                type="button"
                className="rounded bg-accent px-3 py-1 text-paper"
                disabled={report === null}
                onClick={() => {
                  apply.mutate();
                }}
              >
                {t('exchange.apply')}
              </button>
              <button
                type="button"
                className="underline"
                onClick={() => {
                  cancel.mutate();
                }}
              >
                {t('exchange.cancel')}
              </button>
            </div>
          </>
        )}
        {done && (
          <p role="status" className="text-sm">
            {t('exchange.applied')}
          </p>
        )}
        {report && <Report r={report} />}
        <p className="text-xs opacity-70">{t('exchange.rules')}</p>
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}

export function ExchangePage() {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t('exchange.title')}</h1>
      <p className="text-sm opacity-80">{t('exchange.intro')}</p>
      <ExportSection />
      <ImportSection />
    </div>
  );
}
