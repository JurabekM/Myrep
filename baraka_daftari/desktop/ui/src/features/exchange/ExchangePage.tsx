import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type ImportReportDto } from '../../bindings';
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
  const [saved, setSaved] = useState<string | null>(null);
  const last = status.data?.last_export ?? null;
  const exp = useMutation({
    mutationFn: () => unwrap(commands.exportBaraka(pw, incremental && last !== null)),
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
    </div>
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
