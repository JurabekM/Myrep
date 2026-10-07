import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type PlanDto, type RecoveryDto } from '../../bindings';

import { Calculator } from './Calculator';
import { Planner } from './Planner';
import { RecoveryCard } from './RecoveryCard';
import { Sellables } from './Sellables';

vi.mock('../../bindings', () => ({
  commands: {
    recoveryStatus: vi.fn(),
    setBudgetMode: vi.fn(),
    setRecoverySplit: vi.fn(),
    dismissRecoveryNotice: vi.fn(),
    payoffSources: vi.fn(),
    payoffPlan: vi.fn(),
    setClosingOrder: vi.fn(),
    clearClosingOrder: vi.fn(),
    loanCalculator: vi.fn(),
    listSellables: vi.fn(),
    addSellable: vi.fn(),
    sellItem: vi.fn(),
    removeSellable: vi.fn(),
    listDebts: vi.fn(),
  },
}));

// jsdom'da canvas yo'q: grafik komponenti sinovda almashtiriladi.
vi.mock('./BalanceChart', () => ({
  BalanceChart: ({
    series,
    label,
  }: {
    series: { name: string; values: number[] }[];
    label: string;
  }) => (
    <div data-testid="chart" aria-label={label}>
      {series.map((s) => `${s.name}:${String(s.values.length)}`).join('|')}
    </div>
  ),
}));

const money = (formatted: string) => ({ minor: '100', currency: 'UZS', formatted });

function wrap(ui: ReactNode) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {ui}
    </QueryClientProvider>,
  );
}

const recovery: RecoveryDto = {
  mode: 'STANDARD',
  living_bp: 7000,
  extra_bp: 2000,
  savings_bp: 1000,
  suggest_recovery: true,
  reverted_notice: false,
  amounts: {
    living: money("5 600 000 so'm"),
    extra: money("1 600 000 so'm"),
    savings: money("800 000 so'm"),
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.recoveryStatus).mockResolvedValue({ status: 'ok', data: recovery });
  vi.mocked(commands.setBudgetMode).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.setRecoverySplit).mockResolvedValue({ status: 'ok', data: null });
});

describe('RecoveryCard', () => {
  it('faol qarzda rejimni taklif qiladi va yoqish Rustga ketadi', async () => {
    wrap(<RecoveryCard />);
    expect(await screen.findByTestId('suggest')).toBeInTheDocument();
    expect(screen.getByTestId('split-amounts')).toHaveTextContent('1 600 000');
    await userEvent.click(screen.getByRole('button', { name: 'Rejimni yoqish' }));
    await waitFor(() => {
      expect(commands.setBudgetMode).toHaveBeenCalledWith('DEBT_RECOVERY');
    });
  });

  it('jamg‘arma ulushi 1% dan kam bo‘lsa ogohlantiradi va saqlashga yo‘l qo‘ymaydi', async () => {
    wrap(<RecoveryCard />);
    const sv = await screen.findByLabelText('Kelajagim (%)');
    const save = screen.getByRole('button', { name: 'Ulushlarni saqlash' });
    await userEvent.clear(sv);
    await userEvent.type(sv, '0');
    expect(screen.getByTestId('savings-warning')).toBeInTheDocument();
    expect(save).toBeDisabled();
    // 70 / 25 / 5 — yig'indi 100%, jamg'arma 5% → mumkin.
    await userEvent.clear(screen.getByLabelText("Qo'shimcha to'lov (%)"));
    await userEvent.type(screen.getByLabelText("Qo'shimcha to'lov (%)"), '25');
    await userEvent.clear(sv);
    await userEvent.type(sv, '5');
    expect(save).toBeEnabled();
    await userEvent.click(save);
    await waitFor(() => {
      expect(commands.setRecoverySplit).toHaveBeenCalledWith(7000, 2500, 500);
    });
  });

  it('barcha qarz yopilganda avtomatik qaytish haqida xabar chiqadi', async () => {
    vi.mocked(commands.recoveryStatus).mockResolvedValue({
      status: 'ok',
      data: { ...recovery, suggest_recovery: false, reverted_notice: true },
    });
    vi.mocked(commands.dismissRecoveryNotice).mockResolvedValue({ status: 'ok', data: null });
    wrap(<RecoveryCard />);
    const note = await screen.findByTestId('reverted');
    expect(note).toHaveTextContent('barcha qarzlar yopildi');
    expect(note).toHaveTextContent('qorovul pulga');
  });
});

const plan: PlanDto = {
  order: ['a', 'b'],
  manual_order: false,
  lines: [
    { id: 'a', creditor: 'Bank', baseline_months: 7, accelerated_months: 4 },
    { id: 'b', creditor: "Do'st", baseline_months: 5, accelerated_months: 5 },
  ],
  baseline_months: 7,
  accelerated_months: 5,
  months_saved: 2,
  debt_free_baseline: '2027-04-30',
  debt_free_accelerated: '2027-02-28',
};

describe('Planner', () => {
  beforeEach(() => {
    vi.mocked(commands.payoffPlan).mockResolvedValue({ status: 'ok', data: plan });
    vi.mocked(commands.payoffSources).mockResolvedValue({
      status: 'ok',
      data: {
        monthly_share: money("1 600 000 so'm"),
        rescued_available: money("120 000 so'm"),
        sellable_listed: money("500 000 so'm"),
      },
    });
    vi.mocked(commands.setClosingOrder).mockResolvedValue({ status: 'ok', data: null });
  });

  it('odatiy va tezlashtirilgan grafik, qarzsiz kun va manbalar ko‘rinadi', async () => {
    wrap(<Planner />);
    expect(await screen.findByTestId('months-saved')).toHaveTextContent('2 oy erta');
    expect(screen.getByTestId('debt-free-day')).toHaveTextContent('2027-02-28');
    expect(screen.getByTestId('plan-compare')).toHaveTextContent('2027-04-30');
    expect(screen.getByTestId('sources')).toHaveTextContent('1 600 000');
  });

  it('qo‘shimcha summa matni Rustga o‘zgartirilmay yuboriladi; tartib o‘zgartirilganda yangi tartib ketadi', async () => {
    wrap(<Planner />);
    await userEvent.type(
      await screen.findByLabelText("Oylik qo'shimcha to'lov (so'm)"),
      '1 600 000',
    );
    await waitFor(() => {
      expect(commands.payoffPlan).toHaveBeenCalledWith('1 600 000', '');
    });
    await userEvent.click(screen.getByRole('button', { name: "Do'st: yuqoriga" }));
    await waitFor(() => {
      expect(commands.setClosingOrder).toHaveBeenCalledWith(['b', 'a']);
    });
  });

  it('faol qarz bo‘lmasa hech narsa ko‘rsatmaydi', async () => {
    vi.mocked(commands.payoffPlan).mockResolvedValue({ status: 'ok', data: null });
    wrap(<Planner />);
    await waitFor(() => {
      expect(commands.payoffPlan).toHaveBeenCalled();
    });
    expect(screen.queryByTestId('planner')).toBeNull();
  });
});

describe('Calculator', () => {
  it('Anvar: 14 oy → 9 oy; grafik va katta jadval ko‘rinadi', async () => {
    const row = (month: number, balance: string) => ({
      month,
      interest: money('1'),
      principal: money('2'),
      extra: money('3'),
      balance: money(balance),
    });
    vi.mocked(commands.loanCalculator).mockResolvedValue({
      status: 'ok',
      data: {
        baseline: {
          first_payment: money("3 221 476 so'm"),
          months: 14,
          total_interest: money("6 100 675 so'm"),
          schedule: [row(1, '100'), row(2, '50')],
        },
        accelerated: {
          first_payment: money("3 221 476 so'm"),
          months: 9,
          total_interest: money("3 970 186 so'm"),
          schedule: [row(1, '80'), row(2, '0')],
        },
        months_saved: 5,
        interest_saved: money("2 130 489 so'm"),
      },
    });
    wrap(<Calculator />);
    await userEvent.type(await screen.findByLabelText("Asosiy summa (so'm)"), '39 000 000');
    await userEvent.type(screen.getByLabelText('Yillik foiz (%)'), '24');
    await userEvent.type(screen.getByLabelText("Oylik qo'shimcha (so'm)"), '1 600 000');
    await userEvent.click(screen.getByRole('button', { name: 'Hisoblash' }));
    expect(await screen.findByTestId('calc-saved')).toHaveTextContent('5 oy erta');
    expect(commands.loanCalculator).toHaveBeenCalledWith(
      'ANNUITY',
      '39 000 000',
      '24',
      14,
      '1 600 000',
    );
    expect(screen.getByTestId('chart')).toHaveTextContent(
      "Odatiy grafik:2|Qo'shimcha to'lov bilan:2",
    );
    const table = screen.getByRole('table', { name: "To'lov jadvali" });
    expect(within(table).getAllByRole('row').length).toBeGreaterThan(1);
  });
});

describe('Sellables', () => {
  it('sotilgan buyum tushumi tanlangan qarzga yo‘naltiriladi', async () => {
    vi.mocked(commands.listSellables).mockResolvedValue({
      status: 'ok',
      data: [
        {
          id: 's1',
          name: 'Velosiped',
          estimated_price: money("500 000 so'm"),
          unused_since: '2026-01-01',
          status: 'LISTED',
          sold_amount: null,
          sold: false,
        },
      ],
    });
    vi.mocked(commands.listDebts).mockResolvedValue({
      status: 'ok',
      data: [{ id: 'd1', creditor: 'Bank', active: true }],
    } as never);
    vi.mocked(commands.sellItem).mockResolvedValue({ status: 'ok', data: money("300 000 so'm") });
    wrap(<Sellables />);
    await userEvent.type(await screen.findByLabelText('Velosiped: sotilgan narx'), '450 000');
    await userEvent.selectOptions(await screen.findByLabelText('Velosiped: qaysi qarzga'), 'Bank');
    await userEvent.click(screen.getByRole('button', { name: 'Sotildi' }));
    await waitFor(() => {
      expect(commands.sellItem).toHaveBeenCalledWith('s1', '450 000', 'd1');
    });
  });
});
