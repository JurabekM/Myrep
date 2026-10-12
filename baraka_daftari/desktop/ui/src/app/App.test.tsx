import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../i18n';
import { commands } from '../bindings';

import { App } from './App';
import { useNav } from './nav';

vi.mock('../bindings', () => ({
  commands: {
    homeSummary: vi.fn(),
    suggestShare: vi.fn(),
    recordIncome: vi.fn(),
    listIncomes: vi.fn(),
    listObligations: vi.fn(),
    journey: vi.fn(),
    appInfo: vi.fn(),
    lock: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

beforeEach(() => {
  vi.clearAllMocks();
  useNav.setState({ page: 'home', quickEntryOpen: false });
  vi.mocked(commands.homeSummary).mockResolvedValue({
    status: 'ok',
    data: {
      month: '2026-10',
      previous_month: '2026-09',
      today: '2026-10-07',
      week_start: '2026-10-02',
      self_paid: money("0 so'm"),
      self_paid_bp: 0,
      income: money("0 so'm"),
      month_result: money("0 so'm"),
      vault_balance: money("0 so'm"),
      streak_weeks: 0,
      best_streak_weeks: 0,
      saved_days: 0,
      rule: { kind: 'Percent', bp: 500 },
      rate_suggestion_bp: null,
      pending_withdrawals: 0,
    },
  });
  vi.mocked(commands.journey).mockResolvedValue({
    status: 'ok',
    data: {
      chapters: [],
      current_id: 'ch01',
      current_title: 'Bob',
      opened_this_week: false,
      week_start: '2026-10-02',
      week_tasks: [],
      week_done: 0,
      unlock: null,
      policy: { window_weeks: 3, min_satisfied_weeks: 2, min_tasks_per_week: 2 },
    },
  });
  vi.mocked(commands.listObligations).mockResolvedValue({ status: 'ok', data: [] });
  vi.mocked(commands.listIncomes).mockResolvedValue({ status: 'ok', data: [] });
  vi.mocked(commands.appInfo).mockResolvedValue({
    version: '0.1.0',
    templates_approved: false,
    contract_pdf_available: false,
    quick_hotkey_registered: true,
  });
});

function renderApp() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  );
}

describe('App', () => {
  it('Ctrl+N tez kiritish oynasini ochadi', async () => {
    renderApp();
    await screen.findByTestId('self-paid');
    await userEvent.keyboard('{Control>}n{/Control}');
    expect(await screen.findByRole('dialog', { name: 'Yangi daromad' })).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(useNav.getState().quickEntryOpen).toBe(false);
  });

  it("navigatsiya sahifalarni almashtiradi va disklеymer har doim ko'rinadi", async () => {
    renderApp();
    await userEvent.click(await screen.findByRole('button', { name: 'Majburiyatlar' }));
    expect(await screen.findByRole('heading', { name: "Doimiy to'lovlar" })).toBeInTheDocument();
    expect(screen.getByText(/Fatvo yoki moliyaviy maslahat emas/)).toBeInTheDocument();
  });

  it('Ctrl+K palitrasi: matn bilan filtrlanadi va sahifaga o‘tadi', async () => {
    renderApp();
    await screen.findByTestId('self-paid');
    await userEvent.keyboard('{Control>}k{/Control}');
    const input = await screen.findByPlaceholderText('Sahifa yoki amal nomini yozing…');
    await userEvent.type(input, 'qarz');
    await userEvent.keyboard('{Enter}');
    await waitFor(() => {
      expect(useNav.getState().page).toBe('debts');
    });
    expect(useNav.getState().paletteOpen).toBe(false);
  });

  it('Ctrl+K palitrasi Esc bilan yopiladi', async () => {
    renderApp();
    await screen.findByTestId('self-paid');
    await userEvent.keyboard('{Control>}k{/Control}');
    await screen.findByPlaceholderText('Sahifa yoki amal nomini yozing…');
    await userEvent.keyboard('{Escape}');
    await waitFor(() => {
      expect(useNav.getState().paletteOpen).toBe(false);
    });
  });

  it('Ctrl+P chop etish oynasini ochadi', async () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => undefined);
    renderApp();
    await screen.findByTestId('self-paid');
    await userEvent.keyboard('{Control>}p{/Control}');
    expect(print).toHaveBeenCalledTimes(1);
    print.mockRestore();
  });

  it("Ctrl+Alt+B band bo'lsa ogohlantirish ko'rinadi", async () => {
    vi.mocked(commands.appInfo).mockResolvedValue({
      version: '0.1.0',
      templates_approved: false,
      contract_pdf_available: false,
      quick_hotkey_registered: false,
    });
    renderApp();
    expect(await screen.findByRole('note')).toHaveTextContent('Ctrl+Alt+B band');
  });
});
