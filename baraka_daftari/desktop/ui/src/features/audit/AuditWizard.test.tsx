import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type OverviewDto } from '../../bindings';

import { AuditWizard } from './AuditWizard';

vi.mock('../../bindings', () => ({
  commands: { auditSetCategory: vi.fn() },
}));

const set = vi.mocked(commands.auditSetCategory);
const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

const overview: OverviewDto = {
  month: '2026-09',
  income: money("8 000 000 so'm"),
  obligations: money("5 350 000 so'm"),
  expenses: money("1 650 000 so'm"),
  savings: money("0 so'm"),
  month_result: money("1 000 000 so'm"),
  unexplained: money("1 000 000 so'm"),
  categories: ['Oziq-ovqat', 'Benzin', 'Telefon'].map((name, i) => ({
    category_id: `c${String(i)}`,
    name,
    owner: null,
    amount: money("0 so'm"),
  })),
  owners: [{ owner: 'BANK', amount: money("5 350 000 so'm"), bp: 6688 }],
  self_paid_bp: 0,
};

function renderWizard(onClose = vi.fn()) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuditWizard month="2026-09" overview={overview} onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

beforeEach(() => {
  vi.clearAllMocks();
  set.mockResolvedValue({ status: 'ok', data: null });
});

describe('AuditWizard', () => {
  it("oxirgi qadamgacha faqat klaviatura bilan o'tiladi (sichqonchasiz)", async () => {
    renderWizard();
    // 1-qadam: matn yozish (avtofokus) + Enter.
    expect(screen.getByText('Oziq-ovqat')).toBeInTheDocument();
    await userEvent.keyboard('650000{Enter}');
    await screen.findByText('Benzin');
    // 2-qadam: bo'sh qoldirib o'tkazish.
    await userEvent.keyboard('{Enter}');
    await screen.findByText('Telefon');
    // 3-qadam.
    await userEvent.keyboard('50000{Enter}');
    await screen.findByText('Audit natijasi');

    expect(set.mock.calls).toEqual([
      ['2026-09', 'c0', '650000'],
      ['2026-09', 'c2', '50000'],
    ]);
    expect(screen.getByTestId('unexplained')).toHaveTextContent("1 000 000 so'm");
  });

  it('Shift+Enter orqaga qaytaradi', async () => {
    renderWizard();
    await userEvent.keyboard('1{Enter}');
    await screen.findByText('Benzin');
    await userEvent.keyboard('{Shift>}{Enter}{/Shift}');
    await screen.findByText('Oziq-ovqat');
  });

  it('Esc ustani yopadi', async () => {
    const onClose = renderWizard();
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });

  it("Rust xatosi ko'rsatiladi va keyingi qadamga o'tilmaydi", async () => {
    set.mockResolvedValue({ status: 'error', error: { kind: 'InvalidAmount' } });
    renderWizard();
    await userEvent.keyboard('abc{Enter}');
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Summani raqam bilan yozing');
    });
    expect(screen.getByText('Oziq-ovqat')).toBeInTheDocument();
  });
});
