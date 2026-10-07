import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { useNav } from '../../app/nav';
import { commands } from '../../bindings';

import { CouncilMode } from './CouncilMode';

vi.mock('../../bindings', () => ({
  commands: {
    homeSummary: vi.fn(),
    auditOverview: vi.fn(),
    havasReport: vi.fn(),
    listCategories: vi.fn(),
    listMembers: vi.fn(),
    setNecessity: vi.fn(),
    consentLimit: vi.fn(),
    proposeLimit: vi.fn(),
    exportCouncilPdf: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '1', currency: 'UZS', formatted });

beforeEach(() => {
  vi.clearAllMocks();
  useNav.setState({ page: 'council' });
  vi.mocked(commands.homeSummary).mockResolvedValue({
    status: 'ok',
    data: {
      month: '2026-10', today: '2026-10-07', week_start: '2026-10-02', previous_month: '2026-09',
      self_paid: money('0'), self_paid_bp: 0, income: money('0'), month_result: money('0'),
      vault_balance: money('0'), streak_weeks: 0, best_streak_weeks: 0, saved_days: 0,
      rule: { kind: 'Percent', bp: 500 }, rate_suggestion_bp: null, pending_withdrawals: 0,
    },
  });
  vi.mocked(commands.auditOverview).mockResolvedValue({
    status: 'ok',
    data: {
      month: '2026-09', income: money("8 000 000 so'm"), obligations: money('0'), expenses: money('0'),
      savings: money('0'), month_result: money("1 000 000 so'm"), unexplained: money("1 000 000 so'm"),
      categories: [], owners: [], self_paid_bp: 0,
    },
  });
  vi.mocked(commands.havasReport).mockResolvedValue({
    status: 'ok',
    data: {
      month: '2026-09', limit: null, pending: null, spent: money("0 so'm"), state: null, used_bp: null,
      ostentation: { ...money(''), minor: '0' }, debt_funded: { ...money(''), minor: '0' },
      charity: { ...money(''), minor: '0' }, gifts_excluded: { ...money(''), minor: '0' },
    },
  });
  vi.mocked(commands.listCategories).mockResolvedValue({
    status: 'ok',
    data: [
      { id: 'c1', name: 'Telefon', necessity: 'KERAK', is_charity: false, is_habit: false, last_change: 'Dilnoza, 2026-10-01' },
      { id: 'c2', name: 'Sadaqa', necessity: 'KERAK', is_charity: true, is_habit: false, last_change: null },
    ],
  });
  vi.mocked(commands.listMembers).mockResolvedValue({
    status: 'ok',
    data: [
      { id: 'm1', name: 'Karim', role: 'ADULT', has_pin: true },
      { id: 'm2', name: 'Aziza', role: 'CHILD', has_pin: false },
    ],
  });
  vi.mocked(commands.setNecessity).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.exportCouncilPdf).mockResolvedValue({ status: 'ok', data: 'bayonnoma-2026-09.pdf' });
});

function renderCouncil() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <CouncilMode />
    </QueryClientProvider>,
  );
}

describe('CouncilMode', () => {
  it("4 qadam ketma-ket: ko'rib chiqish → toifalar → chegara → bayonnoma", async () => {
    renderCouncil();
    expect(await screen.findByText("Hisobga olinmagan summa".slice(0, 0) + '8 000 000 so\'m')).toBeInTheDocument();
    const next = screen.getByRole('button', { name: 'Keyingisi' });
    const back = screen.getByRole('button', { name: 'Orqaga' });
    expect(back).toBeDisabled();

    await userEvent.click(next);
    expect(await screen.findByText('Telefon')).toBeInTheDocument();
    await userEvent.click(next);
    expect(await screen.findByText(/Chegarani bir kishi bir o'zi belgilamaydi/)).toBeInTheDocument();
    await userEvent.click(next);
    expect(await screen.findByRole('button', { name: 'PDF bayonnomani saqlash' })).toBeInTheDocument();
    expect(next).toBeDisabled();
  });

  it("toifa tanlanganda kim o'zgartirayotgani bilan Rustga yuboriladi; faqat kattalar tanlanadi", async () => {
    renderCouncil();
    await userEvent.click(await screen.findByRole('button', { name: 'Keyingisi' }));
    const group = await screen.findByRole('group', { name: 'Telefon' });
    expect(screen.queryByRole('option', { name: 'Aziza' })).not.toBeInTheDocument();
    await userEvent.click(within(group).getByRole('button', { name: 'Havas' }));
    await waitFor(() => {
      expect(commands.setNecessity).toHaveBeenCalledWith('c1', 'HAVAS', 'm1');
    });
    expect(screen.getByText('Dilnoza, 2026-10-01')).toBeInTheDocument();
    expect(screen.getByText(/Sadaqa \(sadaqa\)/)).toBeInTheDocument();
  });

  it('PDF saqlash: fayl nomi ko‘rsatiladi; bekor qilinsa hech narsa chiqmaydi', async () => {
    renderCouncil();
    const next = await screen.findByRole('button', { name: 'Keyingisi' });
    await userEvent.click(next);
    await userEvent.click(next);
    await userEvent.click(next);
    await userEvent.click(await screen.findByRole('button', { name: 'PDF bayonnomani saqlash' }));
    expect(await screen.findByRole('status')).toHaveTextContent('bayonnoma-2026-09.pdf');
    expect(commands.exportCouncilPdf).toHaveBeenCalledWith('2026-09');
  });

  it('Esc kengashdan chiqaradi', async () => {
    renderCouncil();
    await screen.findByRole('region', { name: 'Oila kengashi' });
    await userEvent.keyboard('{Escape}');
    expect(useNav.getState().page).toBe('family');
  });
});
