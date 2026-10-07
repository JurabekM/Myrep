import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';

import { QuickExpenseWindow } from './QuickExpenseWindow';

vi.mock('../../bindings', () => ({
  commands: {
    vaultState: vi.fn(),
    homeSummary: vi.fn(),
    listCategories: vi.fn(),
    addExpenses: vi.fn(),
    suggestCategory: vi.fn(),
    hideQuickWindow: vi.fn(),
  },
}));

function renderQuick() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <QuickExpenseWindow />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.hideQuickWindow).mockResolvedValue(undefined);
});

describe('QuickExpenseWindow', () => {
  it("qulfli bo'lsa faqat xabar ko'rsatadi va hech qanday ma'lumot so'ramaydi", async () => {
    vi.mocked(commands.vaultState).mockResolvedValue({
      status: 'ok',
      data: { kind: 'Locked', retry_after_secs: 0 },
    });
    renderQuick();
    expect(await screen.findByTestId('quick-locked')).toBeInTheDocument();
    expect(commands.homeSummary).not.toHaveBeenCalled();
    expect(commands.listCategories).not.toHaveBeenCalled();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.getByTestId('quick-locked').textContent).not.toMatch(/\d/);
  });

  it("ochiq bo'lsa xarajatni bugungi sana bilan saqlaydi va oynani yashiradi", async () => {
    vi.mocked(commands.vaultState).mockResolvedValue({ status: 'ok', data: { kind: 'Unlocked' } });
    vi.mocked(commands.homeSummary).mockResolvedValue({
      status: 'ok',
      data: { today: '2026-10-07' },
    } as never);
    vi.mocked(commands.listCategories).mockResolvedValue({
      status: 'ok',
      data: [{ id: 'c1', name: 'Oziq-ovqat' }],
    } as never);
    vi.mocked(commands.addExpenses).mockResolvedValue({ status: 'ok', data: [] } as never);
    renderQuick();
    const amount = await screen.findByRole('textbox', { name: /summa/i });
    await screen.findByText('Oziq-ovqat');
    await userEvent.type(amount, '25000');
    await userEvent.click(screen.getByRole('button', { name: /saqla|qo'sh/i }));
    await vi.waitFor(() => {
      expect(commands.addExpenses).toHaveBeenCalledTimes(1);
    });
    const arg = vi.mocked(commands.addExpenses).mock.calls[0]?.[0];
    expect(arg?.[0]).toMatchObject({ date: '2026-10-07', category_id: 'c1', amount: '25000' });
    await vi.waitFor(() => {
      expect(commands.hideQuickWindow).toHaveBeenCalled();
    });
  });
});
