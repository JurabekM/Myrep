import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type DebtDto, type DebtOverviewDto, type ReceivableDto } from '../../bindings';

import { DebtsPage } from './DebtsPage';

vi.mock('../../bindings', () => ({
  commands: {
    debtOverview: vi.fn(),
    listDebts: vi.fn(),
    listReceivables: vi.fn(),
    listGoals: vi.fn(),
    payDebt: vi.fn(),
    addDebt: vi.fn(),
    debtBurdenPreview: vi.fn(),
    addReceivable: vi.fn(),
    returnReceivable: vi.fn(),
    receiptDetails: vi.fn(),
    saveReceiptDetails: vi.fn(),
    exportReceiptPdf: vi.fn(),
    setDebtEarlyTerms: vi.fn(),
    removeDebt: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '1', currency: 'UZS', formatted });
const zero = { minor: '0', currency: 'UZS', formatted: "0 so'm" };

const overview: DebtOverviewDto = {
  active_count: 1,
  total_remaining: money("9 000 000 so'm"),
  nasiya_remaining: zero,
  monthly_load: money("1 500 000 so'm"),
  burden_bp: 1875,
  excess_total: money("29 000 000 so'm"),
  has_markup_debt: true,
  any_overdue: false,
  receivables_outstanding: money("200 000 so'm"),
};

const debt: DebtDto = {
  id: 'd1',
  creditor: 'Ipak Yoli',
  creditor_type: 'BANK',
  reason: 'to‘y',
  principal: money("40 000 000 so'm"),
  schedule_kind: 'ANNUITY',
  monthly: money("1 500 000 so'm"),
  due_date: '2027-06-07',
  borrowed_on: '2025-10-07',
  early_terms: null,
  closed_on: null,
  active: true,
  paid: money("60 000 000 so'm"),
  total_scheduled: money("69 000 000 so'm"),
  remaining: money("9 000 000 so'm"),
  markup: money("29 000 000 so'm"),
  has_markup: true,
  cost: {
    total: money("69 000 000 so'm"),
    excess: money("29 000 000 so'm"),
    excess_bp: 4203,
  },
  next_due: { due_on: '2026-10-01', amount: money("1 500 000 so'm") },
  overdue: true,
  instalments: [{ due_on: '2026-10-01', amount: money("1 500 000 so'm") }],
  check: null,
  equivalences: [
    { goal_name: 'Kontrakt', goal_target: money("20 000 000 so'm"), times_milli: '1450' },
  ],
};

const receivable: ReceivableDto = {
  id: 'r1',
  debtor: "Qo'shni",
  amount: money("200 000 so'm"),
  returned: zero,
  outstanding: money("200 000 so'm"),
  given_on: '2026-09-01',
  due_on: '2026-10-05',
  note: null,
  due: true,
};

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <DebtsPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.debtOverview).mockResolvedValue({ status: 'ok', data: overview });
  vi.mocked(commands.listDebts).mockResolvedValue({ status: 'ok', data: [debt] });
  vi.mocked(commands.listReceivables).mockResolvedValue({ status: 'ok', data: [receivable] });
  vi.mocked(commands.listGoals).mockResolvedValue({ status: 'ok', data: [] });
  vi.mocked(commands.payDebt).mockResolvedValue({ status: 'ok', data: debt });
  vi.mocked(commands.addDebt).mockResolvedValue({ status: 'ok', data: debt });
  vi.mocked(commands.debtBurdenPreview).mockResolvedValue({ status: 'ok', data: 2500 });
  vi.mocked(commands.receiptDetails).mockResolvedValue({
    status: 'ok',
    data: {
      lender: 'Ipak Yoli',
      borrower: 'Men',
      amount: money("40 000 000 so'm"),
      given_on: '2025-10-07',
      due_on: '2027-06-07',
      has_markup: true,
      witnesses: ['Dilshod'],
      confirmed_by_counterparty: false,
    },
  });
  vi.mocked(commands.saveReceiptDetails).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.exportReceiptPdf).mockResolvedValue({
    status: 'ok',
    data: 'qarz-tilxati.pdf',
  });
});

describe('DebtsPage', () => {
  it('haqiqiy narx, ustama bayrog‘i, muddati o‘tgan to‘lov va imkoniyat narxi ko‘rinadi', async () => {
    renderPage();
    expect(await screen.findByTestId('debt-total')).toHaveTextContent("9 000 000 so'm");
    const card = await screen.findByTestId('debt-Ipak Yoli');
    expect(within(card).getByTestId('cost-Ipak Yoli')).toHaveTextContent(
      "Asosiy summa: 40 000 000 so'm → Jami to'lanadi: 69 000 000 so'm → Ortiqcha: 29 000 000 so'm",
    );
    expect(within(card).getByTestId('cost-Ipak Yoli')).toHaveTextContent('42,03%');
    expect(within(card).getByTestId('equivalence')).toHaveTextContent('1,4 baravariga');
    expect(within(card).getByTestId('markup-flag')).toBeInTheDocument();
    expect(within(card).getByTestId('next-due')).toHaveTextContent(
      'Muddati o‘tgan'.replace('‘', "'"),
    );
    expect(screen.getByTestId('debt-overview')).toHaveTextContent('18,75%');
  });

  it('to‘lov summa matni o‘zgartirilmay Rustga ketadi', async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText("Ipak Yoli: to'lov summasi"), '1 500 000');
    await userEvent.click(screen.getByRole('button', { name: "To'lash" }));
    await waitFor(() => {
      expect(commands.payDebt).toHaveBeenCalledWith('d1', '1 500 000');
    });
  });

  it('berilgan qarzda foiz maydoni yo‘q; muddat kelganda xushmuomala eslatma chiqadi', async () => {
    renderPage();
    const sec = await screen.findByTestId('receivables');
    expect(await within(sec).findByTestId('rec-due')).toHaveTextContent('yumshoq eslatib');
    // Hech bir maydon foiz/ustama deb nomlanmagan.
    for (const el of within(sec).getAllByRole('textbox')) {
      const name = el.getAttribute('aria-label') ?? '';
      expect(name.toLowerCase()).not.toMatch(/foiz|ustama|percent|interest/);
    }
    expect(within(sec).queryByText(/foiz|ustama/i, { selector: 'label' })).toBeNull();
  });

  it('yangi qarz: avval «to‘xta va o‘yla», so‘ng reja; saqlashda javoblar yuboriladi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: "Qarz qo'shish" }));
    expect(await screen.findByTestId('friction')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Hashamat'));
    await userEvent.selectOptions(screen.getByLabelText('Foizsiz muqobil bormi?'), 'Qorovul pul');
    await userEvent.click(screen.getByRole('button', { name: 'Davom etish' }));

    const form = screen.getByRole('heading', { name: 'Yangi qarz' }).closest('form');
    if (!form) throw new Error('forma yo‘q');
    const f = within(form);
    const save = f.getByRole('button', { name: 'Saqlash' });
    expect(save).toBeDisabled();
    await userEvent.type(f.getByLabelText('Kreditor'), 'Anor bank');
    await userEvent.type(f.getByLabelText("Asosiy summa (so'm)"), '3 000 000');
    await userEvent.type(f.getByLabelText("1-to'lov sanasi"), '2026-11-07');
    await userEvent.type(f.getByLabelText("1-to'lov summasi"), '3 000 000');
    expect(await screen.findByTestId('burden-preview')).toHaveTextContent('25%');
    await userEvent.click(save);
    await waitFor(() => {
      expect(commands.addDebt).toHaveBeenCalledTimes(1);
    });
    const input = vi.mocked(commands.addDebt).mock.calls[0]?.[0];
    expect(input).toMatchObject({
      creditor: 'Anor bank',
      principal: '3 000 000',
      schedule_kind: 'MANUAL',
      fixed: null,
      rows: [{ due: '2026-11-07', amount: '3 000 000' }],
      check: { need: 'LUXURY', alternative: 'GUARD' },
    });
  });

  it('teng bo‘laklar turida ustama kiritilsa qizil ogohlantirish chiqadi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: "Qarz qo'shish" }));
    await userEvent.click(screen.getByLabelText(/allaqachon olganman/));
    const form = screen.getByRole('heading', { name: 'Yangi qarz' }).closest('form');
    if (!form) throw new Error('forma yo‘q');
    const f = within(form);
    await userEvent.selectOptions(f.getByLabelText('Jadval turi'), "Teng bo'laklar (ustama bilan)");
    expect(screen.queryByTestId('markup-warning')).toBeNull();
    await userEvent.clear(f.getByLabelText("Ustama jami (so'm)"));
    await userEvent.type(f.getByLabelText("Ustama jami (so'm)"), '500 000');
    expect(screen.getByTestId('markup-warning')).toHaveTextContent('ribo');
  });

  it('tilxat: qo‘lda imzolash rejimida PDF imzosiz so‘raladi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Jadval va tilxat' }));
    const panel = await screen.findByTestId('receipt-panel');
    expect(within(panel).getByRole('alert')).toHaveTextContent('foizsiz qarz emas');
    await userEvent.click(within(panel).getByRole('button', { name: 'PDF saqlash' }));
    await waitFor(() => {
      expect(commands.exportReceiptPdf).toHaveBeenCalledWith('DEBT', 'd1', null, null);
    });
    expect(commands.saveReceiptDetails).toHaveBeenCalledWith('DEBT', 'd1', ['Dilshod', ''], false);
    expect(await within(panel).findByRole('status')).toHaveTextContent('qarz-tilxati.pdf');
  });
});
