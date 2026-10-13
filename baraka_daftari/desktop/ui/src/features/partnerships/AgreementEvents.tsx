import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { ReviewSession } from './ReviewSession';

const input = 'mt-1 block w-full rounded border border-line-strong bg-transparent p-1';

/**
 * Kelishuv voqealari (SPEC 2F.4, 2F.8): «bajara olmayapman» hodisasi va nizo ochish / hakam qarori.
 * Har bir amal jurnalga yoziladi; band darhol ko'rsatiladi. Maqsad — aybdor qidirish emas.
 */
export function AgreementEvents({ p }: { p: PartnershipDto }) {
  const agreement = p.agreement;
  if (
    !agreement ||
    agreement.legacy ||
    agreement.status === 'DRAFT' ||
    agreement.status === 'CLOSED'
  ) {
    return null;
  }
  return (
    <div className="mt-3 space-y-3 text-sm" data-testid="agreement-events">
      <DutyList p={p} />
      <Dispute p={p} />
      <ReviewSession p={p} />
    </div>
  );
}

function DutyList({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState<number | null>(null);
  const [reason, setReason] = useState('');
  const [proposal, setProposal] = useState('');
  const [saved, setSaved] = useState(false);
  const duties = p.agreement?.duties ?? [];
  const report = useMutation({
    mutationFn: (index: number) =>
      unwrap(commands.reportDutyIncident(p.id, index, reason.trim(), proposal.trim())),
    onSuccess: async () => {
      setOpen(null);
      setReason('');
      setProposal('');
      setSaved(true);
      await queryClient.invalidateQueries();
    },
  });
  if (duties.length === 0) return null;
  const submit = (e: FormEvent, index: number) => {
    e.preventDefault();
    setSaved(false);
    report.mutate(index);
  };
  return (
    <section data-testid="duty-list">
      <h3 className="font-medium">{t('partner.events.dutiesTitle')}</h3>
      <ol className="mt-1 space-y-2">
        {duties.map((d, i) => (
          <li
            key={i}
            className="rounded border border-line p-2"
            data-testid={`duty-item-${String(i)}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                {t('partner.events.clause', { n: i + 1, text: d.text, owner: d.owner_name })}
              </span>
              <button
                type="button"
                className="underline"
                aria-expanded={open === i}
                onClick={() => {
                  setSaved(false);
                  setOpen(open === i ? null : i);
                }}
              >
                {t('partner.events.cantDo')}
              </button>
            </div>
            {open === i && (
              <form
                className="mt-2 space-y-2"
                onSubmit={(e) => {
                  submit(e, i);
                }}
                data-testid="duty-incident-form"
              >
                <p className="text-xs opacity-80">
                  {t('partner.events.ifNotDone', { text: d.if_not_done })}
                </p>
                <label className="block">
                  {t('partner.events.reason')}
                  <input
                    className={input}
                    required
                    value={reason}
                    onChange={(e) => {
                      setReason(e.target.value);
                    }}
                  />
                </label>
                <label className="block">
                  {t('partner.events.proposal')}
                  <input
                    className={input}
                    value={proposal}
                    onChange={(e) => {
                      setProposal(e.target.value);
                    }}
                  />
                </label>
                <button
                  type="submit"
                  className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
                  disabled={reason.trim() === '' || report.isPending}
                >
                  {t('partner.events.submitIncident')}
                </button>
              </form>
            )}
          </li>
        ))}
      </ol>
      {saved && (
        <p role="status" className="mt-1">
          {t('partner.events.incidentSaved')}
        </p>
      )}
      {report.error && <p role="alert">{errorMessage(t, report.error)}</p>}
    </section>
  );
}

function Dispute({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const status = p.agreement?.status ?? '';
  const [claimant, setClaimant] = useState(p.parties[0]?.id ?? '');
  const [subject, setSubject] = useState('');
  const [claim, setClaim] = useState('');
  const [decision, setDecision] = useState('');
  const refresh = () => queryClient.invalidateQueries();
  const open = useMutation({
    mutationFn: () =>
      unwrap(commands.openPartnershipDispute(p.id, claimant, subject.trim(), claim.trim())),
    onSuccess: async () => {
      setSubject('');
      setClaim('');
      await refresh();
    },
  });
  const resolve = useMutation({
    mutationFn: () => unwrap(commands.resolvePartnershipDispute(p.id, decision.trim())),
    onSuccess: async () => {
      setDecision('');
      await refresh();
    },
  });
  const error = [open.error, resolve.error].find((x) => x !== null);
  if (status === 'ACTIVE') {
    return (
      <details className="rounded border border-line p-2" data-testid="dispute-open">
        <summary className="cursor-pointer">{t('partner.events.disputeOpen')}</summary>
        <form
          className="mt-2 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            open.mutate();
          }}
        >
          <label className="block">
            {t('partner.events.claimant')}
            <select
              className={input}
              value={claimant}
              onChange={(e) => {
                setClaimant(e.target.value);
              }}
            >
              {p.parties.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            {t('partner.events.subject')}
            <input
              className={input}
              required
              value={subject}
              onChange={(e) => {
                setSubject(e.target.value);
              }}
            />
          </label>
          <label className="block">
            {t('partner.events.claim')}
            <textarea
              className={input}
              rows={2}
              required
              value={claim}
              onChange={(e) => {
                setClaim(e.target.value);
              }}
            />
          </label>
          <button
            type="submit"
            className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
            disabled={
              subject.trim() === '' || claim.trim() === '' || claimant === '' || open.isPending
            }
          >
            {t('partner.events.submitDispute')}
          </button>
          {error && <p role="alert">{errorMessage(t, error)}</p>}
        </form>
      </details>
    );
  }
  if (status === 'IN_DISPUTE') {
    return (
      <section className="rounded border border-accent p-3" data-testid="dispute-active">
        <p className="font-medium">{t('partner.events.disputeActive')}</p>
        <p className="text-xs opacity-80">{t('partner.events.disputeHint')}</p>
        <form
          className="mt-2 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            resolve.mutate();
          }}
        >
          <label className="block">
            {t('partner.events.decision')}
            <textarea
              className={input}
              rows={2}
              required
              value={decision}
              onChange={(e) => {
                setDecision(e.target.value);
              }}
            />
          </label>
          <button
            type="submit"
            className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
            disabled={decision.trim() === '' || resolve.isPending}
          >
            {t('partner.events.submitDecision')}
          </button>
          {error && <p role="alert">{errorMessage(t, error)}</p>}
        </form>
      </section>
    );
  }
  return null;
}
