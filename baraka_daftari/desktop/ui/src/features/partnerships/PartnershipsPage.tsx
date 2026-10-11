import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto } from '../../bindings';
import { errorMessage, formatBp, unwrap } from '../../lib/api';

import { Buyout } from './Buyout';
import { ContractForm } from './ContractForm';
import { Distribution } from './Distribution';
import { Ledger } from './Ledger';

function Card({ p, onRevise }: { p: PartnershipDto; onRevise: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries();
  const [pins, setPins] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const setPin = (k: string, v: string) => {
    setPins((x) => ({ ...x, [k]: v }));
  };
  const sign = useMutation({
    mutationFn: (v: { party?: string; witness?: string; pinKey?: string }) =>
      unwrap(
        commands.signPartnership(
          p.id,
          v.party ?? null,
          v.witness ?? null,
          v.pinKey ? (pins[v.pinKey] ?? null) : null,
        ),
      ),
    onSuccess: refresh,
  });
  const consent = useMutation({
    mutationFn: (memberId: string) =>
      unwrap(commands.partnershipFamilyConsent(p.id, memberId, pins[`c-${memberId}`] ?? '')),
    onSuccess: refresh,
  });
  const activate = useMutation({
    mutationFn: () => unwrap(commands.activatePartnership(p.id)),
    onSuccess: refresh,
  });
  const end = useMutation({
    mutationFn: () => unwrap(commands.endPartnership(p.id)),
    onSuccess: refresh,
  });
  const pdf = useMutation({
    mutationFn: () => unwrap(commands.exportContractPdf(p.id)),
    onSuccess: (n) => {
      setSaved(n);
    },
  });
  const error = [sign.error, consent.error, activate.error, end.error, pdf.error].find(
    (e) => e !== null,
  );
  const draft = p.status === 'DRAFT';
  return (
    <section className="rounded-lg border border-accent/30 p-5" data-testid={`ps-${p.name}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">
          {p.name}{' '}
          <span className="text-sm font-normal opacity-70">
            · {t(`partner.kinds.${p.kind}`)} · {t('partner.versionN', { n: p.version })}
          </span>
        </h2>
        <span className="rounded border border-accent/40 px-2 text-sm" data-testid="ps-status">
          {t(`partner.statuses.${p.status}`)}
        </span>
      </div>
      <p className="text-sm opacity-80">
        {t('partner.summary', { term: p.term_months, capital: p.total_capital.formatted })}
      </p>

      <ul className="mt-3 space-y-2">
        {p.parties.map((x) => (
          <li key={x.id} className="text-sm" data-testid={`party-${x.name}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <strong>{x.name}</strong> — {t(`partner.roles.${x.role}`)} ·{' '}
                {t('partner.shareIs', { bp: formatBp(x.share_bp) })} · {x.capital_total.formatted}
              </span>
              {x.signed ? (
                <span role="status">{t('partner.signed')}</span>
              ) : draft ? (
                <span className="flex items-center gap-2">
                  {x.member_id && (
                    <input
                      type="password"
                      inputMode="numeric"
                      maxLength={6}
                      aria-label={t('partner.pinFor', { name: x.name })}
                      className="w-24 rounded border border-accent/50 bg-transparent p-1"
                      value={pins[x.id] ?? ''}
                      onChange={(e) => {
                        setPin(x.id, e.target.value);
                      }}
                    />
                  )}
                  <button
                    type="button"
                    className="rounded border border-accent px-3 py-0.5"
                    onClick={() => {
                      sign.mutate({ party: x.id, pinKey: x.member_id ? x.id : undefined });
                    }}
                  >
                    {x.member_id ? t('partner.signPin') : t('partner.signManual', { name: x.name })}
                  </button>
                </span>
              ) : null}
            </div>
            <ul className="ml-4 list-disc text-xs opacity-80">
              {x.items.map((c) => (
                <li key={c.description}>
                  {c.description} — {c.value.formatted}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>

      {p.witnesses.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm">
          {p.witnesses.map((w) => (
            <li
              key={w.name}
              className="flex items-center justify-between gap-2"
              data-testid={`witness-${w.name}`}
            >
              <span>{t('partner.witnessIs', { name: w.name })}</span>
              {w.signed ? (
                <span role="status">{t('partner.signed')}</span>
              ) : draft ? (
                <button
                  type="button"
                  className="rounded border border-accent px-3 py-0.5"
                  onClick={() => {
                    sign.mutate({ witness: w.name });
                  }}
                >
                  {t('partner.signManual', { name: w.name })}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {p.self_receives_capital && draft && (
        <div className="mt-3 rounded bg-accent/10 p-3 text-sm" data-testid="family-consent">
          <p className="font-medium">{t('partner.consentTitle')}</p>
          <p className="text-xs opacity-80">{t('partner.consentHint')}</p>
          <ul className="mt-1 space-y-1">
            {p.consents.map((c) => (
              <li key={c.member_id} className="flex items-center justify-between gap-2">
                <span>{c.name}</span>
                {c.consented ? (
                  <span role="status">{t('partner.consented')}</span>
                ) : (
                  <span className="flex items-center gap-2">
                    <input
                      type="password"
                      inputMode="numeric"
                      maxLength={6}
                      aria-label={t('partner.pinFor', { name: c.name })}
                      className="w-24 rounded border border-accent/50 bg-transparent p-1"
                      value={pins[`c-${c.member_id}`] ?? ''}
                      onChange={(e) => {
                        setPin(`c-${c.member_id}`, e.target.value);
                      }}
                    />
                    <button
                      type="button"
                      className="rounded border border-accent px-3 py-0.5"
                      onClick={() => {
                        consent.mutate(c.member_id);
                      }}
                    >
                      {t('partner.consentGive', { name: c.name })}
                    </button>
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs">{t('partner.notDebt')}</p>
        </div>
      )}

      {draft && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
            disabled={p.blocker !== null}
            onClick={() => {
              activate.mutate();
            }}
          >
            {t('partner.activate')}
          </button>
          {p.blocker && (
            <span className="text-sm" data-testid="ps-blocker">
              {t(`partner.blockers.${p.blocker}`)}
            </span>
          )}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-3 text-sm">
        {p.status !== 'ENDED' && (
          <button type="button" className="underline" onClick={onRevise}>
            {t('partner.revise')}
          </button>
        )}
        <button
          type="button"
          className="underline"
          onClick={() => {
            pdf.mutate();
          }}
        >
          {t('partner.pdf')}
        </button>
        {p.status === 'ACTIVE' && (
          <button
            type="button"
            className="underline"
            onClick={() => {
              end.mutate();
            }}
          >
            {t('partner.end')}
          </button>
        )}
      </div>
      {saved && (
        <p role="status" className="text-sm">
          {t('receipt.saved', { name: saved })}
        </p>
      )}

      <div className="mt-4 space-y-3">
        <Distribution p={p} />
        {p.kind === 'MUSHARAKA' && <Buyout p={p} />}
        {p.status !== 'DRAFT' && <Ledger p={p} />}
      </div>

      <details className="mt-3 text-sm">
        <summary>{t('partner.history', { n: p.versions.length })}</summary>
        <ul className="mt-1 space-y-2">
          {p.versions.map((v) => (
            <li key={v.version}>
              <pre className="whitespace-pre-wrap text-xs">{v.snapshot}</pre>
            </li>
          ))}
        </ul>
      </details>
      {error ? (
        <p role="alert" className="mt-2 text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </section>
  );
}

export function PartnershipsPage() {
  const { t } = useTranslation();
  const [mode, setMode] = useState<string>('list');
  const list = useQuery({
    queryKey: ['partnerships'],
    queryFn: () => unwrap(commands.listPartnerships()),
  });
  const info = useQuery({ queryKey: ['app-info'], queryFn: () => commands.appInfo() });
  const reviseTarget = list.data?.find((p) => p.id === mode);
  return (
    <div className="space-y-4">
      {info.data?.templates_approved === false && (
        <p
          role="note"
          className="rounded border border-accent/50 p-3 text-sm"
          data-testid="template-notice"
        >
          {t('partner.templateUnapproved')}
        </p>
      )}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('nav.partnerships')}</h1>
        {mode === 'list' && (
          <button
            type="button"
            className="rounded bg-accent px-4 py-2 text-paper"
            onClick={() => {
              setMode('new');
            }}
          >
            {t('partner.new')}
          </button>
        )}
      </div>
      <p className="text-sm opacity-80">{t('partner.intro')}</p>
      <p className="text-xs opacity-70">{t('partner.regulatory')}</p>
      {mode === 'new' && (
        <ContractForm
          onDone={() => {
            setMode('list');
          }}
        />
      )}
      {reviseTarget && (
        <ContractForm
          existing={reviseTarget}
          onDone={() => {
            setMode('list');
          }}
        />
      )}
      {list.data?.map((p) => (
        <Card
          key={p.id}
          p={p}
          onRevise={() => {
            setMode(p.id);
          }}
        />
      ))}
      {list.data?.length === 0 && mode === 'list' && (
        <p className="opacity-70">{t('partner.empty')}</p>
      )}
    </div>
  );
}
