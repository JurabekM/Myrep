import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';

import { WeekSheet } from './WeekSheet';

vi.mock('../../bindings', () => ({
  commands: {
    homeSummary: vi.fn(),
    listCategories: vi.fn(),
    suggestCategory: vi.fn(),
    addExpenses: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.homeSummary).mockResolvedValue({
    status: 'ok',
    data: {
      month: '2026-10',
      today: '2026-10-07',
      week_start: '2026-10-02',
      previous_month: '2026-09',
      self_paid: money('0'),
      self_paid_bp: 0,
      income: money('0'),
      month_result: money('0'),
      vault_balance: money('0'),
      streak_weeks: 0,
      best_streak_weeks: 0,
      saved_days: 0,
      rule: { kind: 'Percent', bp: 500 },
      rate_suggestion_bp: null,
      pending_withdrawals: 0,
    },
  });
  vi.mocked(commands.listCategories).mockResolvedValue({
    status: 'ok',
    data: [
      {
        id: 'c1',
        name: 'Oziq-ovqat',
        necessity: 'ZARUR',
        is_charity: false,
        is_habit: false,
        last_change: null,
      },
      {
        id: 'c2',
        name: 'Gazak va ichimlik',
        necessity: 'HAVAS',
        is_charity: false,
        is_habit: false,
        last_change: null,
      },
    ],
  });
  vi.mocked(commands.suggestCategory).mockResolvedValue({ status: 'ok', data: 'c2' });
  vi.mocked(commands.addExpenses).mockResolvedValue({ status: 'ok', data: 2 });
});

function renderSheet() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <WeekSheet />
    </QueryClientProvider>,
  );
}

describe('WeekSheet', () => {
  it("hafta kunlari juma'dan bugungacha ko'rsatiladi (kelajak sanasi yo'q)", async () => {
    renderSheet();
    const date = await screen.findByLabelText('Sana');
    const options = within(date)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(options).toEqual([
      '2026-10-02',
      '2026-10-03',
      '2026-10-04',
      '2026-10-05',
      '2026-10-06',
      '2026-10-07',
    ]);
  });

  it("izoh yozilganda kategoriya oxirgi shunday xarajatdan avtomatik to'ldiriladi", async () => {
    renderSheet();
    await screen.findByLabelText('Sana');
    await screen.findByRole('option', { name: 'Gazak va ichimlik' });
    await userEvent.type(screen.getByLabelText('Nima uchun'), 'somsa');
    await userEvent.tab();
    await waitFor(() => {
      expect(screen.getByLabelText('Kategoriya')).toHaveValue('c2');
    });
    expect(commands.suggestCategory).toHaveBeenCalledWith('somsa');
  });

  it("summada Enter yangi qator ochadi, Ctrl+Enter hamma to'ldirilgan qatorni saqlaydi", async () => {
    renderSheet();
    await screen.findByRole('option', { name: 'Oziq-ovqat' });
    await userEvent.type(
      screen.getAllByLabelText("Summa (so'm)")[0] as HTMLElement,
      '12000{Enter}',
    );
    const amounts = screen.getAllByLabelText("Summa (so'm)");
    expect(amounts).toHaveLength(2);
    await userEvent.type(amounts[1] as HTMLElement, '5000');
    await userEvent.selectOptions(screen.getAllByLabelText('Kategoriya')[1] as HTMLElement, 'c1');
    await userEvent.keyboard('{Control>}{Enter}{/Control}');
    await waitFor(() => {
      expect(commands.addExpenses).toHaveBeenCalledTimes(1);
    });
    const items = vi.mocked(commands.addExpenses).mock.calls[0]?.[0] ?? [];
    expect(items).toHaveLength(2);
    expect(items[0]).toMatchObject({
      date: '2026-10-07',
      amount: '12000',
      channel: 'CASH',
      is_gift: false,
    });
    expect(items[1]).toMatchObject({ amount: '5000', category_id: 'c1' });
  });

  it("bo'sh qatorlar yuborilmaydi va saqlash tugmasi o'chiq", async () => {
    renderSheet();
    await screen.findByLabelText('Sana');
    expect(screen.getByRole('button', { name: 'Saqlash (0)' })).toBeDisabled();
  });

  it("belgilar (sovg'a, qarzga) Rustga yuboriladi va xato ko'rsatiladi", async () => {
    vi.mocked(commands.addExpenses).mockResolvedValue({
      status: 'error',
      error: { kind: 'InvalidAmount' },
    });
    renderSheet();
    await screen.findByRole('option', { name: 'Oziq-ovqat' });
    await userEvent.type(screen.getByLabelText("Summa (so'm)"), 'abc');
    await userEvent.click(screen.getByRole('checkbox', { name: "Sovg'a" }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'Qarzga' }));
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash (1)' }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Summani raqam bilan yozing');
    });
    expect(vi.mocked(commands.addExpenses).mock.calls[0]?.[0][0]).toMatchObject({
      is_gift: true,
      funded_by_debt: true,
    });
  });
});
