import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type HomeDto } from '../../bindings';

import { HomePage } from './HomePage';
import { homeSlots } from './slots';

vi.mock('../../bindings', () => ({
  commands: { homeSummary: vi.fn(), setRule: vi.fn() },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

const home: HomeDto = {
  month: '2026-10',
  previous_month: '2026-09',
  self_paid: money("400 000 so'm"),
  self_paid_bp: 500,
  income: money("8 000 000 so'm"),
  month_result: money("1 000 000 so'm"),
  vault_balance: money("1 400 000 so'm"),
  streak_weeks: 4,
  best_streak_weeks: 6,
  saved_days: 12,
  rule: { kind: 'Percent', bp: 500 },
  rate_suggestion_bp: 600,
  pending_withdrawals: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.homeSummary).mockResolvedValue({ status: 'ok', data: home });
  vi.mocked(commands.setRule).mockResolvedValue({ status: 'ok', data: null });
});

function renderHome() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <HomePage />
    </QueryClientProvider>,
  );
}

describe('HomePage', () => {
  it('birinchi raqam — "o\'zingizga to\'ladingiz" (slot tartibi)', async () => {
    expect(homeSlots[0]?.id).toBe('self-paid');
    renderHome();
    const first = await screen.findByTestId('self-paid');
    expect(first).toHaveTextContent("400 000 so'm");
    const headings = screen.getAllByRole('heading', { level: 2 });
    expect(headings[0]).toHaveTextContent("Shu oy o'zingizga to'ladingiz");
  });

  it("Kelajagim balansi, ketma-ketlik va oy yakunini ko'rsatadi", async () => {
    renderHome();
    expect(await screen.findByTestId('vault-balance')).toHaveTextContent("1 400 000 so'm");
    expect(screen.getByTestId('streak')).toHaveTextContent('4 hafta');
    expect(screen.getByText("1 000 000 so'm")).toBeInTheDocument();
  });

  it('ulushni oshirish taklifini qabul qilish setRule chaqiradi', async () => {
    renderHome();
    expect(await screen.findByText(/6% ga oshiramizmi/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ha, oshiramiz' }));
    expect(commands.setRule).toHaveBeenCalledWith({ kind: 'PERCENT', value: '600' });
  });

  it("taklif bo'lmasa tugma yo'q", async () => {
    vi.mocked(commands.homeSummary).mockResolvedValue({
      status: 'ok',
      data: { ...home, rate_suggestion_bp: null },
    });
    renderHome();
    await screen.findByTestId('self-paid');
    expect(screen.queryByRole('button', { name: 'Ha, oshiramiz' })).not.toBeInTheDocument();
  });
});
