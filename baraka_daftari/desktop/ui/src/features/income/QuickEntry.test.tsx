import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { useNav } from '../../app/nav';
import { commands } from '../../bindings';

import { QuickEntry } from './QuickEntry';

vi.mock('../../bindings', () => ({
  commands: { suggestShare: vi.fn(), recordIncome: vi.fn() },
}));

const suggestShare = vi.mocked(commands.suggestShare);
const recordIncome = vi.mocked(commands.recordIncome);

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

function renderEntry() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <QuickEntry />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useNav.setState({ quickEntryOpen: true });
  suggestShare.mockResolvedValue({
    status: 'ok',
    data: {
      share: money("40 000 so'm"),
      allocated_this_month: money("0 so'm"),
      rule: { kind: 'Percent', bp: 500 },
    },
  });
  recordIncome.mockResolvedValue({
    status: 'ok',
    data: { income_id: 'i1', share: money("40 000 so'm"), vault_balance: money("40 000 so'm") },
  });
});

describe('QuickEntry', () => {
  it('summa yozilganda ulush taklif qilinadi va Enter taklifni qabul qiladi (2 harakat)', async () => {
    renderEntry();
    await userEvent.keyboard('800000');
    await waitFor(() => {
      expect(screen.getByTestId('share-suggestion')).toHaveTextContent(
        "Shundan 40 000 so'm — kelajagingiz uchun.",
      );
    });
    expect(suggestShare).toHaveBeenLastCalledWith('800000');

    await userEvent.keyboard('{Enter}');
    await waitFor(() => {
      expect(recordIncome).toHaveBeenCalledWith({
        amount: '800000',
        source: 'DAILY_WORK',
        channel: 'CASH',
        share: null,
      });
    });
    await waitFor(() => {
      expect(useNav.getState().quickEntryOpen).toBe(false);
    });
  });

  it("ulush qo'lda o'zgartirilsa shu summa yuboriladi", async () => {
    renderEntry();
    await userEvent.type(screen.getByLabelText("Summa (so'm)"), '500000');
    await userEvent.type(screen.getByLabelText("Ulushni o'zgartirish (ixtiyoriy)"), '0');
    await userEvent.keyboard('{Enter}');
    await waitFor(() => {
      expect(recordIncome).toHaveBeenCalledWith(
        expect.objectContaining({ amount: '500000', share: '0' }),
      );
    });
  });

  it("bo'sh summa bilan yuborilmaydi", async () => {
    renderEntry();
    await userEvent.keyboard('{Enter}');
    expect(recordIncome).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Saqlash' })).toBeDisabled();
  });

  it("Rust xatosini ko'rsatadi va oynani yopmaydi", async () => {
    recordIncome.mockResolvedValue({ status: 'error', error: { kind: 'InvalidAmount' } });
    renderEntry();
    await userEvent.keyboard('12abc{Enter}');
    await waitFor(() => {
      expect(screen.getAllByRole('alert')[0]).toHaveTextContent('Summani raqam bilan yozing');
    });
    expect(useNav.getState().quickEntryOpen).toBe(true);
  });
});
