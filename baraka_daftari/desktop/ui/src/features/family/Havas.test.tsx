import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type HavasDto } from '../../bindings';

import { ConsentPanel, HavasStatus, ProposeForm } from './Havas';

vi.mock('../../bindings', () => ({
  commands: { consentLimit: vi.fn(), proposeLimit: vi.fn(), listMembers: vi.fn() },
}));

const money = (formatted: string, minor = '1') => ({ minor, currency: 'UZS', formatted });
const zero = money("0 so'm", '0');

const base: HavasDto = {
  month: '2026-10',
  limit: money("1 000 000 so'm"),
  pending: null,
  spent: money("850 000 so'm"),
  state: 'NEAR',
  used_bp: 8500,
  ostentation: zero,
  debt_funded: zero,
  charity: zero,
  gifts_excluded: zero,
};

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.listMembers).mockResolvedValue({
    status: 'ok',
    data: [
      { id: 'm1', name: 'Karim', role: 'ADULT', has_pin: true },
      { id: 'm2', name: 'Dilnoza', role: 'ADULT', has_pin: true },
      { id: 'm3', name: 'Aziza', role: 'CHILD', has_pin: false },
    ],
  });
  vi.mocked(commands.consentLimit).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.proposeLimit).mockResolvedValue({ status: 'ok', data: null });
});

describe('HavasStatus', () => {
  it("80% dan keyin yumshoq ogohlantirish, taqiqsiz; 100% dan keyin ham taqiq yo'q", () => {
    const { rerender } = wrap(<HavasStatus report={base} />);
    expect(screen.getByRole('status')).toHaveTextContent('Taqiq yo‘q'.replace('‘', "'"));
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <HavasStatus report={{ ...base, state: 'OVER', used_bp: 12000 }} />
      </QueryClientProvider>,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Chegaradan oshdi');
    expect(screen.getByRole('status')).toHaveTextContent('Taqiq yo\'q');
  });

  it("chegara faol bo'lmasa ogohlantirish yo'q va tushuntirish bor", () => {
    wrap(<HavasStatus report={{ ...base, limit: null, state: null, used_bp: null }} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByText(/Faol chegara yo'q/)).toBeInTheDocument();
  });

  it("sadaqa, sovg'a va qarz bilan havas alohida ko'rsatiladi", () => {
    wrap(
      <HavasStatus
        report={{ ...base, charity: money("100 000 so'm"), gifts_excluded: money("40 000 so'm"), debt_funded: money("200 000 so'm") }}
      />,
    );
    expect(screen.getByText(/Sadaqa \(isrof emas, alohida\)/)).toBeInTheDocument();
    expect(screen.getByText(/Sovg'alar \(hisobga kirmagan\)/)).toBeInTheDocument();
    expect(screen.getByText(/qarz bilan qilingan havas/)).toBeInTheDocument();
  });
});

describe('ConsentPanel', () => {
  const pending: HavasDto = {
    ...base,
    limit: null,
    state: null,
    pending: {
      limit_id: 'L1',
      amount: money("1 000 000 so'm"),
      consented: ['Karim'],
      missing: [{ id: 'm2', name: 'Dilnoza' }],
    },
  };

  it("rozilik faqat 6 raqamli PIN bilan yuboriladi va PIN tozalanadi", async () => {
    wrap(<ConsentPanel report={pending} />);
    const pin = screen.getByLabelText("Dilnoza PIN'i");
    const agree = screen.getByRole('button', { name: 'Roziman' });
    expect(agree).toBeDisabled();
    await userEvent.type(pin, '22a2222');
    expect(pin).toHaveValue('222222');
    await userEvent.click(agree);
    await waitFor(() => {
      expect(commands.consentLimit).toHaveBeenCalledWith('L1', 'm2', '222222');
    });
    await waitFor(() => {
      expect(pin).toHaveValue('');
    });
  });

  it("noto'g'ri PIN xatosi ko'rsatiladi", async () => {
    vi.mocked(commands.consentLimit).mockResolvedValue({ status: 'error', error: { kind: 'MemberWrongPin' } });
    wrap(<ConsentPanel report={pending} />);
    await userEvent.type(screen.getByLabelText("Dilnoza PIN'i"), '000000');
    await userEvent.click(screen.getByRole('button', { name: 'Roziman' }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent("PIN noto'g'ri.");
    });
  });

  it("taklif bo'lmasa hech narsa chizilmaydi", () => {
    const { container } = wrap(<ConsentPanel report={base} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ProposeForm', () => {
  it("faqat PIN'i bor kattalar taklif qila oladi; PIN to'liq bo'lmaguncha tugma o'chiq", async () => {
    wrap(<ProposeForm />);
    const select = await screen.findByLabelText('Kim taklif qiladi');
    await screen.findByRole('option', { name: 'Karim' });
    expect(screen.queryByRole('option', { name: 'Aziza' })).not.toBeInTheDocument();
    const button = screen.getByRole('button', { name: 'Chegara taklif qilish' });
    await userEvent.type(screen.getByLabelText('Oylik chegara (so\'m)'), '1000000');
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Sizning PIN'), '111111');
    expect(button).toBeEnabled();
    await userEvent.selectOptions(select, 'm2');
    await userEvent.click(button);
    await waitFor(() => {
      expect(commands.proposeLimit).toHaveBeenCalledWith('m2', '111111', '1000000');
    });
  });
});
