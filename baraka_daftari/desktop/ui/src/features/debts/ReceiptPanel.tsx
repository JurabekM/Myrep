import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

import { SignaturePad } from './SignaturePad';

type Mode = 'PRINT' | 'DRAW';

/**
 * Qarz tilxati: guvohlar, ikkinchi tomon tasdig'i va PDF. Imzo: «chop etib qo'lda imzolash» yoki
 * sichqoncha/pero bilan chizish. Yuridik kuch haqida va'da yo'q (PDF'da yozilgan).
 */
export function ReceiptPanel({ kind, id }: { kind: 'DEBT' | 'RECEIVABLE'; id: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const details = useQuery({
    queryKey: ['receipt', kind, id],
    queryFn: () => unwrap(commands.receiptDetails(kind, id)),
  });
  const [witnesses, setWitnesses] = useState(['', '']);
  const [confirmed, setConfirmed] = useState(false);
  const [mode, setMode] = useState<Mode>('PRINT');
  const [lender, setLender] = useState<number[] | null>(null);
  const [borrower, setBorrower] = useState<number[] | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    const d = details.data;
    if (d) {
      setWitnesses([d.witnesses[0] ?? '', d.witnesses[1] ?? '', ...d.witnesses.slice(2)]);
      setConfirmed(d.confirmed_by_counterparty);
    }
  }, [details.data]);

  const save = useMutation({
    mutationFn: () => unwrap(commands.saveReceiptDetails(kind, id, witnesses, confirmed)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['receipt', kind, id] }),
  });
  const exportPdf = useMutation({
    mutationFn: async () => {
      await unwrap(commands.saveReceiptDetails(kind, id, witnesses, confirmed));
      return unwrap(
        commands.exportReceiptPdf(
          kind,
          id,
          mode === 'DRAW' ? lender : null,
          mode === 'DRAW' ? borrower : null,
        ),
      );
    },
    onSuccess: (name) => {
      setSaved(name);
    },
  });
  const d = details.data;
  if (!d) return null;
  const error = [save.error, exportPdf.error].find((e) => e !== null);
  return (
    <div className="mt-3 space-y-3 rounded border border-accent/30 p-3" data-testid="receipt-panel">
      <h4 className="font-semibold">{t('receipt.title')}</h4>
      <p className="text-sm opacity-80">
        {t('receipt.parties', {
          lender: d.lender,
          borrower: d.borrower,
          amount: d.amount.formatted,
        })}
      </p>
      {d.has_markup && (
        <p role="alert" className="text-sm font-semibold">
          {t('receipt.markupWarning')}
        </p>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        {witnesses.map((w, i) => (
          <label key={i} className="block text-sm">
            {t('receipt.witness', { n: i + 1 })}
            <input
              className="mt-1 block w-full rounded border border-accent/50 bg-transparent p-1"
              value={w}
              onChange={(e) => {
                setWitnesses((prev) => prev.map((x, j) => (j === i ? e.target.value : x)));
              }}
            />
          </label>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => {
            setConfirmed(e.target.checked);
          }}
        />
        {t('receipt.confirmed')}
      </label>
      <fieldset className="text-sm">
        <legend className="font-medium">{t('receipt.signMode')}</legend>
        {(['PRINT', 'DRAW'] as const).map((m) => (
          <label key={m} className="mr-4 inline-flex items-center gap-1">
            <input
              type="radio"
              name={`mode-${id}`}
              checked={mode === m}
              onChange={() => {
                setMode(m);
              }}
            />
            {t(`receipt.mode.${m}`)}
          </label>
        ))}
      </fieldset>
      {mode === 'DRAW' && (
        <div className="flex flex-wrap gap-4">
          <SignaturePad
            label={t('receipt.lenderSignature', { name: d.lender })}
            onChange={setLender}
          />
          <SignaturePad
            label={t('receipt.borrowerSignature', { name: d.borrower })}
            onChange={setBorrower}
          />
        </div>
      )}
      <p className="text-xs opacity-70">{t('receipt.legal')}</p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded border border-accent px-3 py-1"
          onClick={() => {
            save.mutate();
          }}
        >
          {t('receipt.save')}
        </button>
        <button
          type="button"
          className="rounded bg-accent px-3 py-1 text-paper"
          onClick={() => {
            exportPdf.mutate();
          }}
        >
          {t('receipt.exportPdf')}
        </button>
      </div>
      {saved && (
        <p role="status" className="text-sm">
          {t('receipt.saved', { name: saved })}
        </p>
      )}
      {error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, error)}
        </p>
      ) : null}
    </div>
  );
}
