import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type CeremonyDto } from '../../bindings';

import { CeremoniesPage } from './CeremoniesPage';

vi.mock('../../bindings', () => ({
  commands: {
    listCeremonies: vi.fn(),
    createCeremony: vi.fn(),
    setCeremonyDate: vi.fn(),
    addCeremonyLine: vi.fn(),
    removeCeremonyLine: vi.fn(),
    recordCeremonyDiscussion: vi.fn(),
    setCeremonyStatus: vi.fn(),
    removeCeremony: vi.fn(),
    compareCeremonies: vi.fn(),
    openGiftGoal: vi.fn(),
    exportCeremonyPdf: vi.fn(),
  },
}));

const money = (formatted: string, minor = '1') => ({ minor, currency: 'UZS', formatted });
const zero = money("0 so'm", '0');

function plan(over: Partial<CeremonyDto> & { name: string; id: string }): CeremonyDto {
  return {
    kind: 'WEDDING',
    date: '2027-05-01',
    status: 'DRAFT',
    discussed: false,
    discussion_note: null,
    lines: [
      {
        id: `${over.id}-l1`,
        name: 'Osh',
        qty: 200,
        unit_price: money("150 000 so'm"),
        total: money("30 000 000 so'm"),
        funding: 'SAVINGS',
      },
    ],
    totals: {
      total: money("30 000 000 so'm"),
      savings: money("30 000 000 so'm"),
      family: zero,
      expected_gifts: zero,
      debt: zero,
      debt_bp: 0,
    },
    confirm_blocker: null,
    ...over,
  };
}

const withDebt = plan({
  id: 'p1',
  name: '3 kunlik, 200 kishi',
  totals: {
    total: money("50 000 000 so'm"),
    savings: money("30 000 000 so'm"),
    family: zero,
    expected_gifts: zero,
    debt: money("20 000 000 so'm"),
    debt_bp: 4000,
  },
  confirm_blocker: 'DISCUSSION_REQUIRED',
});
const small = plan({ id: 'p2', name: '1 kunlik, 100 kishi' });

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <CeremoniesPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.listCeremonies).mockResolvedValue({ status: 'ok', data: [withDebt, small] });
  for (const k of [
    'createCeremony',
    'setCeremonyDate',
    'addCeremonyLine',
    'removeCeremonyLine',
    'recordCeremonyDiscussion',
    'setCeremonyStatus',
    'removeCeremony',
    'openGiftGoal',
  ] as const) {
    vi.mocked(commands[k]).mockResolvedValue({ status: 'ok', data: null } as never);
  }
});

describe('CeremoniesPage', () => {
  it('qarz bor reja muhokamasiz tasdiqlanmaydi: tugma o‘chiq, sabab ko‘rinadi, muhokama bloki chiqadi', async () => {
    renderPage();
    const card = await screen.findByTestId('plan-3 kunlik, 200 kishi');
    expect(within(card).getByTestId('debt-warning')).toHaveTextContent('40%');
    expect(within(card).getByRole('button', { name: 'Tasdiqlash' })).toBeDisabled();
    expect(within(card).getByTestId('blocker')).toHaveTextContent('oilaviy muhokamani');
    expect(within(card).getByTestId('discussion')).toBeInTheDocument();
    // Qarzsiz reja uchun muhokama bloki yo'q va tasdiqlash mumkin.
    const ok = screen.getByTestId('plan-1 kunlik, 100 kishi');
    expect(within(ok).queryByTestId('discussion')).toBeNull();
    expect(within(ok).getByRole('button', { name: 'Tasdiqlash' })).toBeEnabled();
  });

  it('muhokama xulosasi Rustga yuboriladi; tasdiqlash CONFIRMED yuboradi', async () => {
    renderPage();
    const card = await screen.findByTestId('plan-3 kunlik, 200 kishi');
    const disc = within(card).getByTestId('discussion');
    const done = within(disc).getByRole('button', { name: "Muhokama o'tkazildi" });
    expect(done).toBeDisabled();
    await userEvent.type(within(disc).getByLabelText('Muhokama xulosasi'), 'Ixcham qilamiz');
    await userEvent.click(done);
    await waitFor(() => {
      expect(commands.recordCeremonyDiscussion).toHaveBeenCalledWith('p1', 'Ixcham qilamiz');
    });
    await userEvent.click(
      within(screen.getByTestId('plan-1 kunlik, 100 kishi')).getByRole('button', {
        name: 'Tasdiqlash',
      }),
    );
    await waitFor(() => {
      expect(commands.setCeremonyStatus).toHaveBeenCalledWith('p2', 'CONFIRMED');
    });
  });

  it('qator qo‘shish matnlarni o‘zgartirmay yuboradi', async () => {
    renderPage();
    const card = await screen.findByTestId('plan-1 kunlik, 100 kishi');
    const c = within(card);
    await userEvent.type(c.getByLabelText('Qator'), 'Musiqa');
    await userEvent.clear(c.getByLabelText('Miqdor', { selector: 'input' }));
    await userEvent.type(c.getByLabelText('Miqdor', { selector: 'input' }), '2');
    await userEvent.type(c.getByLabelText("Birlik narxi (so'm)"), '5 000 000');
    await userEvent.selectOptions(c.getByLabelText('Manba', { selector: 'select' }), 'Qarz');
    await userEvent.click(c.getByRole('button', { name: "Qator qo'shish" }));
    await waitFor(() => {
      expect(commands.addCeremonyLine).toHaveBeenCalledWith('p2', 'Musiqa', 2, '5 000 000', 'DEBT');
    });
  });

  it('stsenariylarni solishtiradi: 2 tadan kam bo‘lsa tugma o‘chiq', async () => {
    vi.mocked(commands.compareCeremonies).mockResolvedValue({
      status: 'ok',
      data: [
        {
          plan: withDebt,
          cheaper_than_max: zero,
          repay_months: 20,
          repay_too_long: false,
          alternatives: [
            { goal_name: 'Kontrakt', goal_target: money("20 000 000 so'm"), times_milli: '2500' },
          ],
        },
        {
          plan: small,
          cheaper_than_max: money("20 000 000 so'm"),
          repay_months: 0,
          repay_too_long: false,
          alternatives: [],
        },
      ],
    });
    renderPage();
    const sec = await screen.findByTestId('compare');
    const s = within(sec);
    const btn = s.getByRole('button', { name: 'Solishtirish' });
    expect(btn).toBeDisabled();
    await userEvent.click(s.getByLabelText('3 kunlik, 200 kishi'));
    expect(btn).toBeDisabled();
    await userEvent.click(s.getByLabelText('1 kunlik, 100 kishi'));
    await userEvent.type(s.getByLabelText("Oylik to'lov imkoniyati (so'm)"), '1 000 000');
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    const table = await s.findByTestId('compare-table');
    expect(within(table).getByTestId('repay-row')).toHaveTextContent('20 oy');
    expect(table).toHaveTextContent('2,5 baravari');
    expect(commands.compareCeremonies).toHaveBeenCalledWith(['p1', 'p2'], '1 000 000', '');
  });

  it('to‘yona o‘rniga maqsad ochish', async () => {
    renderPage();
    const card = await screen.findByTestId('plan-1 kunlik, 100 kishi');
    await userEvent.type(within(card).getByLabelText("Maqsad summasi (so'm)"), '100 000 000');
    await userEvent.click(within(card).getByRole('button', { name: 'Maqsad ochish' }));
    await waitFor(() => {
      expect(commands.openGiftGoal).toHaveBeenCalledWith('p2', '100 000 000');
    });
  });
});
