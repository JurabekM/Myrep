import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
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
  vi.mocked(commands.listObligations).mockResolvedValue({ status: 'ok', data: [] });
  vi.mocked(commands.listIncomes).mockResolvedValue({ status: 'ok', data: [] });
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
});
