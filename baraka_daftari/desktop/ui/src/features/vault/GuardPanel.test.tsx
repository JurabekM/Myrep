import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type GateDto, type GuardDto } from '../../bindings';

import { GuardPanel } from './GuardPanel';

vi.mock('../../bindings', () => ({
  commands: {
    guardOverview: vi.fn(),
    gateStatus: vi.fn(),
    setDebtPlanDeclaration: vi.fn(),
    bypassGate: vi.fn(),
    revokeGateBypass: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

const guard: GuardDto = {
  monthly_need: money("1 500 000 so'm"),
  target: money("9 000 000 so'm"),
  milestone: money("4 500 000 so'm"),
  balance: money("2 100 000 so'm"),
  growing_balance: money("0 so'm"),
  gap: money("6 900 000 so'm"),
  months_x100: 140,
  milestone_reached: false,
  full_reached: false,
  basis_months: 3,
};

const lockedGate: GateDto = {
  rules_open: false,
  bypassed: false,
  open: false,
  reasons: ['GUARD_BELOW_TARGET', 'INTEREST_DEBT_NO_PLAN'],
  months_x100: 140,
  required_x100: 600,
  has_interest_debt: true,
  has_debt_plan: false,
};

function renderPanel() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <GuardPanel />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.guardOverview).mockResolvedValue({ status: 'ok', data: guard });
  vi.mocked(commands.gateStatus).mockResolvedValue({ status: 'ok', data: lockedGate });
  vi.mocked(commands.bypassGate).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.setDebtPlanDeclaration).mockResolvedValue({ status: 'ok', data: null });
});

describe('GuardPanel', () => {
  it('«1,4 / 6 oy» progressi va birinchi bosqich ko‘rsatiladi', async () => {
    renderPanel();
    expect(await screen.findByTestId('guard-months')).toHaveTextContent('1,4 / 6 oylik zaxira');
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '140');
    expect(screen.getByTestId('guard-milestone')).toHaveTextContent('Birinchi bosqich (3 oy)');
  });

  it('ma‘lumot bo‘lmasa tushuntirish chiqadi, summa to‘qilmaydi', async () => {
    vi.mocked(commands.guardOverview).mockResolvedValue({
      status: 'ok',
      data: { ...guard, basis_months: 0, months_x100: 0 },
    });
    renderPanel();
    expect(await screen.findByTestId('guard-nodata')).toBeInTheDocument();
  });

  it('qulfli bo‘limda sabablar ko‘rsatiladi va chetlab o‘tish tasdiqsiz bajarilmaydi', async () => {
    renderPanel();
    const locked = await screen.findByTestId('gate-locked');
    expect(locked).toHaveTextContent('Qorovul pul: 1,4 / 6 oy');
    expect(locked).toHaveTextContent('qarzdan chiqish rejasi yo‘q'.replace('‘', "'"));
    await userEvent.click(
      screen.getByRole('button', { name: 'Qulfni ongli chetlab o‘tish'.replace('‘', "'") }),
    );
    const confirm = screen.getByRole('button', { name: 'Tasdiqlash va ochish' });
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByLabelText("Xavfni tushundim, o'z tanlovim"));
    await userEvent.click(confirm);
    await waitFor(() => {
      expect(commands.bypassGate).toHaveBeenCalledWith(true);
    });
  });

  it('ochiq darvozada o‘sadigan balans ko‘rinadi; chetlab o‘tilgan bo‘lsa qaytarish tugmasi bor', async () => {
    vi.mocked(commands.gateStatus).mockResolvedValue({
      status: 'ok',
      data: { ...lockedGate, open: true, bypassed: true, reasons: [] },
    });
    renderPanel();
    expect(await screen.findByTestId('gate-open')).toHaveTextContent('ongli tanlovingiz');
    expect(screen.getByRole('button', { name: 'Qulfni qaytarish' })).toBeInTheDocument();
    expect(screen.queryByTestId('gate-locked')).toBeNull();
  });

  it('qarz bayoni Rustga yuboriladi', async () => {
    renderPanel();
    await userEvent.click(await screen.findByLabelText('Qarzdan chiqish rejam bor'));
    await waitFor(() => {
      expect(commands.setDebtPlanDeclaration).toHaveBeenCalledWith(true);
    });
  });
});
