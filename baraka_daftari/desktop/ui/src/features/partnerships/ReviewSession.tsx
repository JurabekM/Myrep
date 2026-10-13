import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type PartnershipDto, type ReviewPartyDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

/** Joriy davr: `YYYY-MM` (mahalliy vaqt bo'yicha). */
function currentPeriod(): string {
  const now = new Date();
  return `${String(now.getFullYear())}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

/**
 * Oylik ochiq hisob ko'rigi (SPEC 2F.5): zanjir holati, har bir tomonning «ko'rdim, roziman» yoki
 * «e'tirozim bor» javobi, davr yozuvlari va yakunda ko'rik bayonnomasi (PDF, zanjir boshi bilan).
 */
export function ReviewSession({ p }: { p: PartnershipDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [period] = useState(currentPeriod);
  const [objecting, setObjecting] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const status = p.agreement?.status ?? '';
  const active = status === 'ACTIVE' || status === 'IN_DISPUTE';
  const review = useQuery({
    queryKey: ['review', p.id, period],
    queryFn: () => unwrap(commands.reviewView(p.id, period)),
    enabled: active,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['review', p.id] });
  const answer = useMutation({
    mutationFn: (v: { party: string; agree: boolean; note: string }) =>
      unwrap(commands.recordReviewAnswer(p.id, period, v.party, v.agree, v.note)),
    onSuccess: async () => {
      setObjecting(null);
      setNote('');
      await refresh();
    },
  });
  const close = useMutation({
    mutationFn: () => unwrap(commands.closeReview(p.id, period)),
    onSuccess: refresh,
  });
  const exportPdf = useMutation({
    mutationFn: () => unwrap(commands.exportReviewPdf(p.id, period)),
  });
  if (!active) return null;
  const r = review.data;
  if (!r) return null;
  const allAnswered = r.parties.every((x) => x.agree !== null);
  const error = [review.error, answer.error, close.error, exportPdf.error].find((x) => x !== null);
  const answerText = (x: ReviewPartyDto) => {
    if (x.agree === true) return t('partner.review.answerAgree');
    if (x.agree === false) return t('partner.review.answerObject', { note: x.note ?? '' });
    return t('partner.review.answerNone');
  };
  return (
    <section className="space-y-2 rounded border border-line p-3" data-testid="review-session">
      <h3 className="font-medium">{t('partner.review.title', { period: r.period })}</h3>
      <p className="text-xs opacity-80">{t('partner.review.hint')}</p>
      {r.chain_intact ? (
        <p className="text-sm" data-testid="review-chain">
          {t('partner.review.chainOk', { n: r.chain_length })}
        </p>
      ) : (
        <p role="alert" className="text-sm font-semibold" data-testid="review-chain">
          {t('partner.review.chainBroken', { n: r.broken_seq ?? 0 })}
        </p>
      )}
      {r.closed &&
        (r.head_matches === false ? (
          <p role="alert" className="text-sm font-semibold" data-testid="review-head">
            {t('partner.review.headMismatch')}
          </p>
        ) : (
          <p role="status" className="text-sm" data-testid="review-head">
            {t('partner.review.headOk')}
          </p>
        ))}
      <ul className="space-y-2">
        {r.parties.map((x) => (
          <li
            key={x.party_id}
            className="rounded border border-line p-2"
            data-testid={`review-party-${x.name}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>{x.name}</span>
              <span className="text-xs">{answerText(x)}</span>
              {!r.closed && (
                <span className="flex gap-3">
                  <button
                    type="button"
                    className="underline"
                    onClick={() => {
                      answer.mutate({ party: x.party_id, agree: true, note: '' });
                    }}
                  >
                    {t('partner.review.agree')}
                  </button>
                  <button
                    type="button"
                    className="underline"
                    aria-expanded={objecting === x.party_id}
                    onClick={() => {
                      setObjecting(objecting === x.party_id ? null : x.party_id);
                    }}
                  >
                    {t('partner.review.object')}
                  </button>
                </span>
              )}
            </div>
            {!r.closed && objecting === x.party_id && (
              <form
                className="mt-2 flex flex-wrap gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  answer.mutate({ party: x.party_id, agree: false, note });
                }}
              >
                <input
                  aria-label={t('partner.review.objectionNote')}
                  className="flex-1 rounded border border-line-strong bg-transparent p-1"
                  required
                  value={note}
                  onChange={(e) => {
                    setNote(e.target.value);
                  }}
                />
                <button
                  type="submit"
                  className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
                  disabled={note.trim() === '' || answer.isPending}
                >
                  {t('partner.review.submitObjection')}
                </button>
              </form>
            )}
          </li>
        ))}
      </ul>
      <details>
        <summary className="cursor-pointer">
          {t('partner.review.ledgerTitle', { n: r.ledger.length })}
        </summary>
        <ul className="mt-1 space-y-1 text-xs">
          {r.ledger.map((l, i) => (
            <li key={i}>
              {`${l.date} · ${l.label}${l.party ? ` · ${l.party}` : ''}${l.amount ? ` · ${l.amount}` : ''}`}
              {` — ${l.note}`}
            </li>
          ))}
        </ul>
      </details>
      <details>
        <summary className="cursor-pointer">
          {t('partner.review.incidentsTitle', { n: r.incidents.length })}
        </summary>
        <ul className="mt-1 space-y-1 text-xs">
          {r.incidents.map((l, i) => (
            <li key={i}>{`${l.date} · ${l.party} — ${l.note}`}</li>
          ))}
        </ul>
      </details>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        {!r.closed && (
          <button
            type="button"
            className="rounded border border-accent px-3 py-0.5 disabled:opacity-50"
            disabled={!allAnswered || close.isPending}
            onClick={() => {
              close.mutate();
            }}
          >
            {t('partner.review.close')}
          </button>
        )}
        <button
          type="button"
          className="underline"
          onClick={() => {
            exportPdf.mutate();
          }}
        >
          {t('partner.review.pdf')}
        </button>
        {exportPdf.data && (
          <span role="status">{t('receipt.saved', { name: exportPdf.data })}</span>
        )}
      </div>
      {error && <p role="alert">{errorMessage(t, error)}</p>}
    </section>
  );
}
