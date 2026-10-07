import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  commands,
  type CsvMappingInput,
  type CsvPreviewDto,
  type CsvResultDto,
} from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';
import { useCategories } from '../../lib/hooks';

const DATE_FORMATS = ['ISO', 'DMY_DOTS', 'DMY_SLASHES', 'YMD_SLASHES'] as const;
const SIGNS = ['NEGATIVE_ARE_EXPENSES', 'POSITIVE_ARE_EXPENSES', 'ABSOLUTE_ALL'] as const;

/** Sarlavhadan ustunni taxmin qilish (faqat qulaylik; foydalanuvchi o'zgartira oladi). */
function guess(headers: string[], re: RegExp, fallback: number): number {
  const i = headers.findIndex((h) => re.test(h));
  return i >= 0 ? i : fallback;
}

function Mapper({ preview, onDone }: { preview: CsvPreviewDto; onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const categories = useCategories();
  const h = preview.headers;
  const [dateCol, setDateCol] = useState(guess(h, /sana|date|vaqt/i, 0));
  const [amountCol, setAmountCol] = useState(guess(h, /summa|amount|sum|miqdor/i, 1));
  const [noteCol, setNoteCol] = useState(guess(h, /izoh|note|desc|tavsif|nomi|purpose/i, -1));
  const [dateFormat, setDateFormat] = useState<(typeof DATE_FORMATS)[number]>('DMY_DOTS');
  const [sign, setSign] = useState<(typeof SIGNS)[number]>('NEGATIVE_ARE_EXPENSES');
  const [categoryId, setCategoryId] = useState('');
  const [result, setResult] = useState<CsvResultDto | null>(null);

  const mapping: CsvMappingInput = {
    date_col: dateCol,
    amount_col: amountCol,
    note_col: noteCol >= 0 ? noteCol : null,
    date_format: dateFormat,
    sign,
  };
  const dry = useQuery({
    queryKey: ['csv-dry', preview.token, dateCol, amountCol, noteCol, dateFormat, sign],
    queryFn: () => unwrap(commands.csvDryRun(preview.token, mapping)),
    retry: false,
  });
  const chosen =
    categoryId ||
    categories.data?.find((c) => c.name === 'Boshqa')?.id ||
    categories.data?.[0]?.id ||
    '';
  const run = useMutation({
    mutationFn: () => unwrap(commands.csvImport(preview.token, mapping, chosen)),
    onSuccess: async (r) => {
      setResult(r);
      await queryClient.invalidateQueries();
    },
  });

  const colSelect = (label: string, value: number, set: (n: number) => void, optional = false) => (
    <label className="block text-sm">
      {label}
      <select
        className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
        value={value}
        onChange={(e) => {
          set(Number(e.target.value));
        }}
      >
        {optional && <option value={-1}>—</option>}
        {h.map((name, i) => (
          <option key={i} value={i}>{`${String(i + 1)}. ${name}`}</option>
        ))}
      </select>
    </label>
  );

  if (result) {
    return (
      <div className="space-y-2" data-testid="csv-result">
        <p className="text-lg font-semibold">{t('csv.done', { n: result.imported })}</p>
        <p className="text-sm">
          {t('csv.doneDetails', {
            dup: result.duplicates,
            skipped: result.skipped_sign,
            errors: result.error_count,
          })}
        </p>
        <ul className="text-sm">
          {result.errors.map((e) => (
            <li key={`${String(e.line)}-${e.reason}`}>
              {t('csv.errorLine', { line: e.line, reason: e.reason })}
            </li>
          ))}
        </ul>
        <button type="button" className="rounded border border-accent px-3 py-1" onClick={onDone}>
          {t('csv.close')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="text-xs" aria-label={t('csv.preview')}>
          <thead>
            <tr>
              {h.map((name, i) => (
                <th key={i} className="border-b border-accent/30 px-2 text-left">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.slice(0, 5).map((row, ri) => (
              <tr key={ri}>
                {row.map((c, ci) => (
                  <td key={ci} className="px-2">
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs opacity-70">{t('csv.rows', { n: preview.total_rows })}</p>
      <div className="flex flex-wrap gap-4">
        {colSelect(t('csv.dateCol'), dateCol, setDateCol)}
        {colSelect(t('csv.amountCol'), amountCol, setAmountCol)}
        {colSelect(t('csv.noteCol'), noteCol, setNoteCol, true)}
        <label className="block text-sm">
          {t('csv.dateFormat')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={dateFormat}
            onChange={(e) => {
              setDateFormat(e.target.value as (typeof DATE_FORMATS)[number]);
            }}
          >
            {DATE_FORMATS.map((f) => (
              <option key={f} value={f}>
                {t(`csv.fmt.${f}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          {t('csv.sign')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={sign}
            onChange={(e) => {
              setSign(e.target.value as (typeof SIGNS)[number]);
            }}
          >
            {SIGNS.map((s) => (
              <option key={s} value={s}>
                {t(`csv.signs.${s}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          {t('csv.defaultCategory')}
          <select
            className="mt-1 block rounded border border-accent/50 bg-transparent p-1"
            value={chosen}
            onChange={(e) => {
              setCategoryId(e.target.value);
            }}
          >
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {dry.data && (
        <p data-testid="csv-dry" className="text-sm">
          {t('csv.dry', {
            ok: dry.data.imported,
            skipped: dry.data.skipped_sign,
            errors: dry.data.error_count,
          })}
        </p>
      )}
      <div role="alert" className="min-h-5 text-sm">
        {run.error ? errorMessage(t, run.error) : dry.error ? errorMessage(t, dry.error) : null}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded bg-accent px-4 py-2 text-paper disabled:opacity-50"
          disabled={run.isPending || chosen === '' || (dry.data?.imported ?? 0) === 0}
          onClick={() => {
            run.mutate();
          }}
        >
          {t('csv.import', { n: dry.data?.imported ?? 0 })}
        </button>
        <button type="button" className="underline" onClick={onDone}>
          {t('csv.cancel')}
        </button>
      </div>
    </div>
  );
}

/** CSV import ustasi: fayl → ustunlarni xaritalash → sinov → import. Bank integratsiyasi emas. */
export function CsvImport() {
  const { t } = useTranslation();
  const [preview, setPreview] = useState<CsvPreviewDto | null>(null);
  const open = useMutation({
    mutationFn: () => unwrap(commands.csvOpen()),
    onSuccess: (p) => {
      if (p) setPreview(p);
    },
  });
  return (
    <section aria-label={t('csv.title')} className="rounded-lg border border-accent/30 p-5">
      <h2 className="text-lg font-semibold">{t('csv.title')}</h2>
      <p className="text-sm opacity-80">{t('csv.hint')}</p>
      {preview ? (
        <div className="mt-3">
          <Mapper
            preview={preview}
            onDone={() => {
              setPreview(null);
            }}
          />
        </div>
      ) : (
        <button
          type="button"
          className="mt-3 rounded border border-accent px-4 py-2"
          disabled={open.isPending}
          onClick={() => {
            open.mutate();
          }}
        >
          {t('csv.choose')}
        </button>
      )}
      <div role="alert" className="min-h-5 text-sm">
        {open.error ? errorMessage(t, open.error) : null}
      </div>
    </section>
  );
}
