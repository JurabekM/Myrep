import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';

import { VaultPage } from './VaultPage';

vi.mock('../../bindings', () => ({
  commands: {
    homeSummary: vi.fn(),
    listWithdrawals: vi.fn(),
    requestWithdrawal: vi.fn(),
    guardOverview: vi.fn(),
    gateStatus: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.homeSummary).mockResolvedValue({
    status: 'ok',
    data: {
      vault_balance: money("5 000 000 so'm"),
      rule: { kind: 'Percent', bp: 500 },
    },
  } as never);
  vi.mocked(commands.listWithdrawals).mockResolvedValue({ status: 'ok', data: [] });
  vi.mocked(commands.guardOverview).mockResolvedValue({
    status: 'error',
    error: { kind: 'NotFound' },
  });
  vi.mocked(commands.gateStatus).mockResolvedValue({
    status: 'error',
    error: { kind: 'NotFound' },
  });
  vi.mocked(commands.requestWithdrawal).mockResolvedValue({
    status: 'ok',
    data: {},
  } as never);
});

describe('VaultPage: pul olish', () => {
  it('favqulodda tasdig‘isiz so‘rov yuborib bo‘lmaydi; tasdiq bilan true yuboriladi', async () => {
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <VaultPage />
      </QueryClientProvider>,
    );
    await userEvent.type(await screen.findByLabelText("Summa (so'm)"), '1000000');
    await userEvent.type(screen.getByLabelText('Nima uchun kerak?'), 'Dori');
    const submit = screen.getByRole('button', { name: "So'rov yuborish" });
    expect(submit).toBeDisabled();
    await userEvent.click(screen.getByLabelText(/haqiqatan favqulodda holat/));
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    await waitFor(() => {
      expect(commands.requestWithdrawal).toHaveBeenCalledWith('1000000', 'Dori', true);
    });
  });
});
