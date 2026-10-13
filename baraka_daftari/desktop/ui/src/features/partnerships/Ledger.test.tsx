import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type LedgerDto, type PartnershipDto } from '../../bindings';

import { Ledger } from './Ledger';

vi.mock('../../bindings', () => ({
  commands: {
    ventureLedger: vi.fn(),
    addVentureEntry: vi.fn(),
    removeVentureEntry: vi.fn(),
    attachEvidence: vi.fn(),
    exportEvidence: vi.fn(),
    closeVenturePeriod: vi.fn(),
    exportPeriodReport: vi.fn(),
  },
}));

const m = (formatted: string) => ({ minor: '1', currency: 'UZS', formatted });

const p = { id: 'p1', name: 'Ustaxona', kind: 'MUDARABA', status: 'ACTIVE' } as PartnershipDto;

const open: LedgerDto['open'] = {
  id: 'per1',
  period_no: 1,
  start_date: '2026-01-01',
  end_date: null,
  closed: false,
  income: m("5 000 000 so'm"),
  expenses: m("1 000 000 so'm"),
  net: m("4 000 000 so'm"),
  entries: [
    {
      id: 'e1',
      kind: 'INCOME',
      description: 'Buyurtma',
      amount: m("5 000 000 so'm"),
      occurred_on: '2026-01-05',
      note: null,
      force_majeure: false,
      attachments: [],
    },
  ],
  distribution: [],
};

function setLedger(over: Partial<LedgerDto>) {
  vi.mocked(commands.ventureLedger).mockResolvedValue({
    status: 'ok',
    data: { open, closed: [], read_only: false, active: true, spike_alert: false, ...over },
  });
}

function renderLedger() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <Ledger p={p} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.addVentureEntry).mockResolvedValue({ status: 'ok', data: {} } as never);
  vi.mocked(commands.closeVenturePeriod).mockResolvedValue({ status: 'ok', data: {} } as never);
});

describe('Ledger', () => {
  it('ochiq davr yozuvlari va jami ko‘rinadi, biznes puli alohida ekani aytiladi', async () => {
    setLedger({});
    renderLedger();
    expect(await screen.findByTestId('entry-Buyurtma')).toBeInTheDocument();
    expect(screen.getByText(/alohida yuritiladi/)).toBeInTheDocument();
    expect(screen.getByText(/Sof: 4 000 000/)).toBeInTheDocument();
  });

  it('foring-major yozuvi chiqim sifatida jo‘natiladi', async () => {
    setLedger({});
    renderLedger();
    await screen.findByTestId('entry-Buyurtma');
    await userEvent.type(screen.getByLabelText('Tavsif'), 'Yong‘in');
    await userEvent.type(screen.getByLabelText("Summa (so'm)"), '300000');
    await userEvent.click(screen.getByLabelText('Bu foring-major (ofat) tufayli zarar'));
    await userEvent.click(screen.getByRole('button', { name: "Yozuvni qo'shish" }));
    await waitFor(() => {
      expect(commands.addVentureEntry).toHaveBeenCalledWith(
        'p1',
        expect.objectContaining({ kind: 'EXPENSE', force_majeure: true, amount: '300000' }),
      );
    });
  });

  it('kapital egasi uchun faqat o‘qish: forma yo‘q', async () => {
    setLedger({ read_only: true });
    renderLedger();
    await screen.findByTestId('entry-Buyurtma');
    expect(screen.getByText(/faqat o'qish/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "Yozuvni qo'shish" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Davrni yopish' })).not.toBeInTheDocument();
  });

  it('davrni yopish buyrug‘i chaqiriladi', async () => {
    setLedger({});
    renderLedger();
    await screen.findByTestId('entry-Buyurtma');
    await userEvent.click(screen.getByRole('button', { name: 'Davrni yopish' }));
    await waitFor(() => {
      expect(commands.closeVenturePeriod).toHaveBeenCalledWith('p1', null, null, false);
    });
  });

  it('katta foyda: tasdiqsiz davr yopilmaydi, tasdiqdan keyin tasdiq yuboriladi', async () => {
    setLedger({ spike_alert: true });
    renderLedger();
    await screen.findByTestId('entry-Buyurtma');
    const close = screen.getByRole('button', { name: 'Davrni yopish' });
    expect(close).toBeDisabled();
    await userEvent.click(
      screen.getByRole('checkbox', { name: "Ikkala tomon 4- va 5-bandlarni qayta o'qib chiqdi" }),
    );
    expect(close).toBeEnabled();
    await userEvent.click(close);
    await waitFor(() => {
      expect(commands.closeVenturePeriod).toHaveBeenCalledWith('p1', null, null, true);
    });
  });

  it('yopilgan davr tahrirlanmasligi aytiladi', async () => {
    setLedger({
      open: null,
      closed: [
        {
          ...open,
          id: 'per0',
          closed: true,
          end_date: '2025-12-31',
          period_no: 1,
        },
      ],
    });
    renderLedger();
    await screen.findByText(/Davr №1/);
    expect(screen.getByText(/tahrirlanmaydi/)).toBeInTheDocument();
  });
});
