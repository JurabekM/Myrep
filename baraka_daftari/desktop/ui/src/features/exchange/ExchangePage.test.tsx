import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';
import { a11yViolations } from '../../lib/axe';

import { ExchangePage } from './ExchangePage';

vi.mock('../../bindings', () => ({
  commands: {
    exchangeStatus: vi.fn(),
    exportBaraka: vi.fn(),
    importBarakaPick: vi.fn(),
    importBarakaPreview: vi.fn(),
    importBarakaApply: vi.fn(),
    importBarakaCancel: vi.fn(),
    openAgreementDispute: vi.fn(),
  },
}));

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ExchangePage />
    </QueryClientProvider>,
  );
}

const report = {
  inserted: 5,
  updated: 2,
  unchanged: 10,
  kept_local: 1,
  adults_without_pin: [],
  forks: [],
  conflicts: [
    {
      table: 'venture_periods',
      id: 'p1',
      kind: 'CLOSED_PERIOD',
      resolution: 'KEPT_LOCAL',
      label: 'Davr 1',
    },
  ],
};

/** Ikki qurilmada kelishuv jurnali #3 dan ayrilgan: mahalliy 4 ta yozuv, fayldagi 3 ta. */
const forkReport = {
  ...report,
  conflicts: [
    {
      table: 'journal_entries',
      id: 'ag1',
      kind: 'JOURNAL',
      resolution: 'SKIPPED',
      label: 'kelishuv jurnali: zanjir ayrilib ketgan (yozuv #3), import to‘xtatildi',
    },
  ],
  forks: [
    {
      agreement_id: 'ag1',
      title: 'Yetkazib berish musharakasi',
      reason: 'zanjir ayrilib ketgan',
      diverged_seq: 3,
      local: {
        count: 4,
        first_seq: 1,
        last_seq: 4,
        head: 'ab'.repeat(32),
        last_date: '2026-10-12',
        last_kind: 'VENTURE_INCOME',
        last_note: 'Buyurtma 2',
      },
      incoming: {
        count: 3,
        first_seq: 1,
        last_seq: 3,
        head: 'cd'.repeat(32),
        last_date: '2026-10-11',
        last_kind: 'VENTURE_INCOME',
        last_note: 'Buyurtma 1',
      },
      parties: [
        { id: 'a', name: 'Karim aka' },
        { id: 'b', name: 'Zamira' },
      ],
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.exchangeStatus).mockResolvedValue({
    status: 'ok',
    data: { last_export: null },
  });
  vi.mocked(commands.exportBaraka).mockResolvedValue({ status: 'ok', data: 'baraka.baraka' });
  vi.mocked(commands.importBarakaPick).mockResolvedValue({ status: 'ok', data: 'telefon.baraka' });
  vi.mocked(commands.importBarakaPreview).mockResolvedValue({ status: 'ok', data: report });
  vi.mocked(commands.importBarakaApply).mockResolvedValue({ status: 'ok', data: report });
});

describe('ExchangePage', () => {
  it('parollar mos kelmasa eksport o‘chiq, mos bo‘lsa to‘liq eksport chaqiriladi', async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText('Fayl paroli'), 'parol-12345');
    await userEvent.type(screen.getByLabelText('Parolni takrorlang'), 'parol-1');
    expect(screen.getByRole('alert')).toHaveTextContent('bir xil emas');
    expect(screen.getByRole('button', { name: 'Eksport qilish' })).toBeDisabled();
    await userEvent.clear(screen.getByLabelText('Parolni takrorlang'));
    await userEvent.type(screen.getByLabelText('Parolni takrorlang'), 'parol-12345');
    // Hali eksport bo‘lmagan: inkremental o‘chiq.
    expect(screen.getByLabelText(/Faqat o‘zgarganlar|Faqat o'zgarganlar/)).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Eksport qilish' }));
    await waitFor(() => {
      expect(commands.exportBaraka).toHaveBeenCalledWith('parol-12345', false, true);
    });
    expect(await screen.findByRole('status')).toHaveTextContent('baraka.baraka');
  });

  it('import: fayl tanlanadi, tekshiriladi, ziddiyatlar ko‘rsatiladi, so‘ng birlashtiriladi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Faylni tanlash' }));
    expect(await screen.findByText(/telefon\.baraka/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Birlashtirish' })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Fayl paroli (import)'), 'parol-12345');
    await userEvent.click(screen.getByRole('button', { name: 'Tekshirish' }));
    const rep = await screen.findByTestId('import-report');
    expect(rep).toHaveTextContent('Yangi: 5');
    expect(screen.getByTestId('conflict-CLOSED_PERIOD')).toHaveTextContent(
      'Yopilgan davr o‘zgartirilmadi'.replace('‘', "'"),
    );
    expect(commands.importBarakaApply).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Birlashtirish' }));
    await waitFor(() => {
      expect(commands.importBarakaApply).toHaveBeenCalledWith('parol-12345');
    });
    expect(await screen.findByText('Birlashtirildi.')).toBeInTheDocument();
  });

  it('noto‘g‘ri parol aniq xato beradi va hisobot ko‘rsatilmaydi', async () => {
    vi.mocked(commands.importBarakaPreview).mockResolvedValue({
      status: 'error',
      error: { kind: 'WrongPassword' },
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Faylni tanlash' }));
    await userEvent.type(await screen.findByLabelText('Fayl paroli (import)'), 'xato-parol');
    await userEvent.click(screen.getByRole('button', { name: 'Tekshirish' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Parol noto');
    expect(screen.queryByTestId('import-report')).not.toBeInTheDocument();
  });

  it('kelishuv jurnali ayrilganda ikki nusxa ko‘rinadi va nizo ochiladi', async () => {
    vi.mocked(commands.importBarakaPreview).mockResolvedValue({ status: 'ok', data: forkReport });
    vi.mocked(commands.openAgreementDispute).mockResolvedValue({ status: 'ok', data: null });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Faylni tanlash' }));
    await userEvent.type(await screen.findByLabelText('Fayl paroli (import)'), 'parol-12345');
    await userEvent.click(screen.getByRole('button', { name: 'Tekshirish' }));
    const card = within(await screen.findByTestId('fork-ag1'));
    expect(card.getByText('Yetkazib berish musharakasi')).toBeInTheDocument();
    expect(card.getByText('Farq yozuv #3 dan boshlanadi.')).toBeInTheDocument();
    expect(card.getByText('Bu qurilmada')).toBeInTheDocument();
    expect(card.getByText('Faylda')).toBeInTheDocument();
    expect(commands.importBarakaApply).not.toHaveBeenCalled();
    await userEvent.click(card.getByRole('button', { name: 'Nizo sifatida ochish' }));
    await userEvent.click(card.getByRole('button', { name: 'Nizoni ochish' }));
    await waitFor(() => {
      expect(commands.openAgreementDispute).toHaveBeenCalledWith(
        'ag1',
        'a',
        'Kelishuv jurnali ayrilib ketdi',
        expect.stringContaining('#3'),
      );
    });
    expect(await card.findByRole('status')).toHaveTextContent('Nizo ochildi');
  });

  it('accessibility: axe buzilish topmaydi', async () => {
    const { container } = renderPage();
    await screen.findByLabelText('Fayl paroli');
    expect(await a11yViolations(container)).toEqual([]);
  });
});
