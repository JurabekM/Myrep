import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type PartnershipDto } from '../../bindings';
import { a11yViolations } from '../../lib/axe';

import { PartnershipsPage } from './PartnershipsPage';

vi.mock('../../bindings', () => ({
  commands: {
    listPartnerships: vi.fn(),
    listMembers: vi.fn(),
    createPartnership: vi.fn(),
    revisePartnership: vi.fn(),
    signPartnership: vi.fn(),
    partnershipFamilyConsent: vi.fn(),
    activatePartnership: vi.fn(),
    endPartnership: vi.fn(),
    previewDistribution: vi.fn(),
    setBuyoutPlan: vi.fn(),
    recordBuyoutPayment: vi.fn(),
    exportContractPdf: vi.fn(),
    checkPartnershipDraft: vi.fn(),
    reportDutyIncident: vi.fn(),
    openPartnershipDispute: vi.fn(),
    resolvePartnershipDispute: vi.fn(),
    reviewView: vi.fn(),
    recordReviewAnswer: vi.fn(),
    closeReview: vi.fn(),
    exportReviewPdf: vi.fn(),
    appInfo: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '1', currency: 'UZS', formatted });
const zero = { minor: '0', currency: 'UZS', formatted: "0 so'm" };

const base: PartnershipDto = {
  id: 'p1',
  name: 'Ustaxona',
  kind: 'MUDARABA',
  term_months: 12,
  report_period: 'MONTHLY',
  end_clause: 'Uskunalar qaytariladi',
  dispute_clause: 'Oqsoqol',
  version: 1,
  status: 'DRAFT',
  parties: [
    {
      id: 'a',
      name: 'Karim aka',
      role: 'CAPITAL_PROVIDER',
      share_bp: 4000,
      member_id: null,
      capital_total: money("8 000 000 so'm"),
      items: [
        {
          description: 'Naqd pul',
          kind: 'CASH',
          value: money("8 000 000 so'm"),
          value_text: '8000000',
        },
      ],
      signed: false,
    },
    {
      id: 'b',
      name: 'Zamira',
      role: 'WORKER',
      share_bp: 6000,
      member_id: 'm1',
      capital_total: zero,
      items: [],
      signed: false,
    },
  ],
  witnesses: [{ name: 'Dilshod', signed: false }],
  total_capital: money("8 000 000 so'm"),
  self_provides_capital: false,
  self_receives_capital: true,
  consents: [{ member_id: 'm1', name: 'Men', consented: false }],
  versions: [{ version: 1, snapshot: 'Ustaxona · 1-versiya' }],
  blocker: 'PARTY_SIGNATURES',
  buyout: null,
  agreement: null,
};

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <PartnershipsPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.appInfo).mockResolvedValue({
    version: '0.1.0',
    templates_approved: false,
    contract_pdf_available: true,
    quick_hotkey_registered: true,
  });
  vi.mocked(commands.listPartnerships).mockResolvedValue({ status: 'ok', data: [base] });
  vi.mocked(commands.listMembers).mockResolvedValue({
    status: 'ok',
    data: [{ id: 'm1', name: 'Men', role: 'ADULT', has_pin: true }],
  });
  vi.mocked(commands.checkPartnershipDraft).mockResolvedValue({
    status: 'ok',
    data: { missing_questions: [], errors: [], pdf: null },
  });
  for (const k of [
    'reportDutyIncident',
    'openPartnershipDispute',
    'resolvePartnershipDispute',
    'recordReviewAnswer',
    'closeReview',
  ] as const) {
    vi.mocked(commands[k]).mockResolvedValue({ status: 'ok', data: null });
  }
  vi.mocked(commands.reviewView).mockResolvedValue({
    status: 'ok',
    data: {
      period: '2026-10',
      closed: false,
      chain_length: 0,
      chain_intact: true,
      broken_seq: null,
      recorded_head: null,
      head_matches: null,
      parties: [],
      ledger: [],
      incidents: [],
    },
  });
  for (const k of [
    'signPartnership',
    'partnershipFamilyConsent',
    'activatePartnership',
    'revisePartnership',
  ] as const) {
    vi.mocked(commands[k]).mockResolvedValue({ status: 'ok', data: null } as never);
  }
});

describe('PartnershipsPage', () => {
  it('relizda shablon tasdiqlanmagan bo‘lsa shartnoma PDF tugmasi yashirin', async () => {
    vi.mocked(commands.appInfo).mockResolvedValue({
      version: '0.1.0',
      templates_approved: false,
      contract_pdf_available: false,
      quick_hotkey_registered: true,
    });
    renderPage();
    const card = await screen.findByTestId('ps-Ustaxona');
    await waitFor(() => {
      expect(within(card).queryByRole('button', { name: 'Shartnoma PDF' })).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('template-notice')).toBeInTheDocument();
  });

  it('accessibility: axe buzilish topmaydi', async () => {
    const { container } = renderPage();
    await screen.findByTestId('ps-Ustaxona');
    expect(await a11yViolations(container)).toEqual([]);
  });

  it('tasdiqlanmagan shablon haqida ogohlantiradi', async () => {
    renderPage();
    expect(await screen.findByTestId('template-notice')).toHaveTextContent('ulamo tasdig');
  });

  it('faollashtirish tugmasi to‘siq bor paytda o‘chiq va sabab ko‘rinadi', async () => {
    renderPage();
    const card = await screen.findByTestId('ps-Ustaxona');
    expect(within(card).getByRole('button', { name: 'Faollashtirish' })).toBeDisabled();
    expect(within(card).getByTestId('ps-blocker')).toHaveTextContent('tomonlar joriy versiyani');
    expect(within(card).getByTestId('family-consent')).toHaveTextContent(
      'qaytarish majburiyati yo',
    );
  });

  it('a‘zo tomon PIN bilan, tashqi tomon va guvoh qo‘lda tasdiqlaydi', async () => {
    renderPage();
    const card = await screen.findByTestId('ps-Ustaxona');
    const c = within(card);
    await userEvent.click(c.getByRole('button', { name: 'Karim aka tasdiqladi' }));
    await waitFor(() => {
      expect(commands.signPartnership).toHaveBeenCalledWith('p1', 'a', null, null, null);
    });
    await userEvent.type(c.getByLabelText('Zamira: PIN'), '111111');
    await userEvent.click(c.getByRole('button', { name: 'PIN bilan tasdiqlash' }));
    await waitFor(() => {
      expect(commands.signPartnership).toHaveBeenCalledWith('p1', 'b', null, null, '111111');
    });
    await userEvent.click(within(c.getByTestId('witness-Dilshod')).getByRole('button'));
    await waitFor(() => {
      expect(commands.signPartnership).toHaveBeenCalledWith('p1', null, 'Dilshod', null, null);
    });
  });

  it('oilaviy rozilik a‘zoning PIN‘i bilan yuboriladi', async () => {
    renderPage();
    const fc = await screen.findByTestId('family-consent');
    await userEvent.type(within(fc).getByLabelText('Men: PIN'), '222222');
    await userEvent.click(within(fc).getByRole('button', { name: 'Men rozilik beradi' }));
    await waitFor(() => {
      expect(commands.partnershipFamilyConsent).toHaveBeenCalledWith('p1', 'm1', '222222');
    });
  });

  it('to‘siq yo‘q bo‘lsa faollashtirish ishlaydi', async () => {
    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, blocker: null }],
    });
    renderPage();
    const btn = within(await screen.findByTestId('ps-Ustaxona')).getByRole('button', {
      name: 'Faollashtirish',
    });
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    await waitFor(() => {
      expect(commands.activatePartnership).toHaveBeenCalledWith('p1');
    });
  });

  it('taqsimot hisobi: beparvolik izohsiz yuborilmaydi, natija ko‘rinadi', async () => {
    vi.mocked(commands.previewDistribution).mockResolvedValue({
      status: 'ok',
      data: [
        { name: 'Karim aka', amount: money("0 so'm") },
        { name: 'Zamira', amount: money("−200 so'm") },
      ],
    });
    renderPage();
    const dist = await screen.findByTestId('distribution');
    const d = within(dist);
    await userEvent.selectOptions(d.getByLabelText('Natija'), 'Zarar');
    await userEvent.type(d.getByLabelText("Summa (so'm)"), '200');
    await userEvent.click(d.getByLabelText('Ishchining beparvoligi'));
    await userEvent.type(d.getByLabelText('Beparvolik izohi (majburiy)'), 'ombor ochiq qoldi');
    await userEvent.click(d.getByRole('button', { name: 'Hisoblash' }));
    await waitFor(() => {
      expect(commands.previewDistribution).toHaveBeenCalledWith(
        'p1',
        'LOSS',
        '200',
        'ombor ochiq qoldi',
      );
    });
    expect(await d.findByTestId('dist-result')).toHaveTextContent('Zamira');
  });

  it('kafolatli summa kiritishga urinish Rustning tushuntirishi bilan rad etiladi', async () => {
    vi.mocked(commands.createPartnership).mockResolvedValue({
      status: 'error',
      error: {
        kind: 'Invalid',
        message:
          "Bu sheriklik emas — ribo yoki qarz: foyda faqat sof foydaning foizi bo'lishi mumkin",
      },
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Yangi shartnoma' }));
    const form = screen.getByTestId('contract-form');
    const f = within(form);
    await userEvent.type(f.getByLabelText('Sheriklik nomi'), 'Test');
    await userEvent.type(f.getByLabelText('1-tomon ismi'), 'A');
    await userEvent.type(f.getByLabelText('2-tomon ismi'), 'B');
    await userEvent.type(f.getByLabelText("Muddat tugaganda nima bo'ladi"), 'qaytariladi');
    await userEvent.type(f.getByLabelText('Nizolarni hal qilish tartibi'), 'oqsoqol');
    await userEvent.type(
      f.getByLabelText("Kapital egasi uchun qat'iy summa (kafolat) — kiritib bo'lmaydi"),
      '5 000 000',
    );
    await userEvent.click(f.getByRole('button', { name: 'Shartnomani saqlash' }));
    expect(await f.findByTestId('form-error')).toHaveTextContent('ribo yoki qarz');
    const arg = vi.mocked(commands.createPartnership).mock.calls[0]?.[0];
    expect(arg?.parties[0]).toMatchObject({
      share_bp: 5000,
      fixed_return: '5 000 000',
      role: 'CAPITAL_PROVIDER',
    });
    expect(arg?.parties[1]).toMatchObject({ share_bp: 5000, role: 'WORKER' });
  });

  it('noto‘g‘ri foyda ulushi matni Rustga yuborilmaydi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Yangi shartnoma' }));
    const f = within(screen.getByTestId('contract-form'));
    await userEvent.clear(f.getByLabelText('1-tomon foyda ulushi (%)'));
    await userEvent.type(f.getByLabelText('1-tomon foyda ulushi (%)'), 'abc');
    await userEvent.click(f.getByRole('button', { name: 'Shartnomani saqlash' }));
    expect(await f.findByTestId('form-error')).toHaveTextContent('foizda yozing');
    expect(commands.createPartnership).not.toHaveBeenCalled();
  });

  it('o‘zgartirish yangi versiya sifatida yuboriladi va oldingi qiymatlar to‘ldiriladi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: "Shartnomani o'zgartirish" }));
    const f = within(screen.getByTestId('contract-form'));
    expect(f.getByLabelText('Sheriklik nomi')).toHaveValue('Ustaxona');
    expect(f.getByLabelText('1-tomon, 1-kapital qiymati')).toHaveValue('8000000');
    await userEvent.click(f.getByRole('button', { name: 'Shartnomani saqlash' }));
    await waitFor(() => {
      expect(commands.revisePartnership).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(commands.revisePartnership).mock.calls[0]?.[0]).toBe('p1');
  });
});

describe('shartnoma ustasi: 9 qadam, maslahat va önizleme', () => {
  it('progress har savolning holatini ko‘rsatadi va önizleme bloklanganini aytadi', async () => {
    vi.mocked(commands.checkPartnershipDraft).mockResolvedValue({
      status: 'ok',
      data: {
        missing_questions: [3, 8, 9],
        errors: [{ question: 4, code: 'PROFIT_SHARES_NOT_100' }],
        pdf: null,
      },
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Yangi shartnoma' }));
    const side = within(screen.getByTestId('wizard-progress'));
    expect(await side.findByText('5 / 9 savol tayyor')).toBeInTheDocument();
    expect(screen.getByTestId('wizard-step-3')).toHaveAttribute('data-state', 'todo');
    expect(screen.getByTestId('wizard-step-4')).toHaveAttribute('data-state', 'wrong');
    expect(screen.getByTestId('wizard-step-1')).toHaveAttribute('data-state', 'done');
    expect(await screen.findByTestId('draft-preview-blocked')).toBeInTheDocument();
  });

  it('maydonga o‘tilganda o‘sha savolning maslahati chiqadi', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Yangi shartnoma' }));
    const f = within(screen.getByTestId('contract-form'));
    await userEvent.click(f.getByLabelText('1-tomon foyda ulushi (%)'));
    expect(
      within(screen.getByTestId('wizard-advice')).getByText(/Foyda faqat sof natijadan/),
    ).toBeInTheDocument();
  });

  it('PDF baytlari kelsa, önizleme iframe’da chiqadi', async () => {
    const createURL = vi.fn(() => 'blob:draft');
    Object.defineProperty(URL, 'createObjectURL', { value: createURL, configurable: true });
    Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), configurable: true });
    vi.mocked(commands.checkPartnershipDraft).mockResolvedValue({
      status: 'ok',
      data: { missing_questions: [], errors: [], pdf: [37, 80, 68, 70] },
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Yangi shartnoma' }));
    const frame = await screen.findByTitle('Shartnoma önizlemasi (PDF)');
    expect(frame).toHaveAttribute('src', 'blob:draft');
    expect(createURL).toHaveBeenCalled();
  });
});

function agreementOf(status: string): NonNullable<PartnershipDto['agreement']> {
  return {
    id: 'ag1',
    status,
    current_version: 1,
    legacy: false,
    missing_questions: [],
    errors: [],
    warnings: [],
    missing_signatures: [],
    journal_length: 0,
    journal_intact: true,
    duties: [
      {
        text: 'Yetkazib berish va hisobot',
        owner_name: 'Karim aka',
        if_not_done: '1 kun ichida xabar beradi',
      },
    ],
    custody_place: 'Anvar hisobi',
    arbiter_name: 'Usta Olim',
    review_date: '2027-10-01',
  };
}

describe('kelishuv voqealari: bajara olmayapman va nizo', () => {
  const agreement = agreementOf;

  it('bajara olmayapman: band darhol ko‘rinadi va hodisa jurnalga yuboriladi', async () => {
    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, status: 'ACTIVE', agreement: agreement('ACTIVE') }],
    });
    renderPage();
    const card = within(await screen.findByTestId('ps-Ustaxona'));
    await userEvent.click(card.getByRole('button', { name: 'Bajara olmayapman' }));
    expect(card.getByTestId('duty-incident-form')).toHaveTextContent(
      'Bajarilmasa: 1 kun ichida xabar beradi',
    );
    await userEvent.type(card.getByLabelText('Sabab'), 'Yo‘l yopiq edi');
    await userEvent.click(card.getByRole('button', { name: 'Hodisani yozish' }));
    await waitFor(() => {
      expect(commands.reportDutyIncident).toHaveBeenCalledWith('p1', 0, 'Yo‘l yopiq edi', '');
    });
    expect(await card.findByRole('status')).toHaveTextContent('Hodisa jurnalga yozildi');
  });

  it('nizo ochiladi, so‘ng hakam qarori bilan yopiladi', async () => {
    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, status: 'ACTIVE', agreement: agreement('ACTIVE') }],
    });
    const { unmount } = renderPage();
    const card = within(await screen.findByTestId('ps-Ustaxona'));
    await userEvent.click(card.getByText('Nizo ochish'));
    await userEvent.type(card.getByLabelText('Mavzu'), 'Foyda hisobi');
    await userEvent.type(card.getByLabelText('Talab'), 'Ulush 60/40 bo‘lsin');
    await userEvent.click(card.getByRole('button', { name: 'Nizoni ochish' }));
    await waitFor(() => {
      expect(commands.openPartnershipDispute).toHaveBeenCalledWith(
        'p1',
        'a',
        'Foyda hisobi',
        'Ulush 60/40 bo‘lsin',
      );
    });
    unmount();

    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, status: 'ACTIVE', agreement: agreement('IN_DISPUTE') }],
    });
    renderPage();
    const again = within(await screen.findByTestId('dispute-active'));
    await userEvent.type(again.getByLabelText('Hakam qarori'), 'Ulush 50/50');
    await userEvent.click(again.getByRole('button', { name: 'Qarorni yozib, nizoni yopish' }));
    await waitFor(() => {
      expect(commands.resolvePartnershipDispute).toHaveBeenCalledWith('p1', 'Ulush 50/50');
    });
  });
});

describe('oylik ko‘rik', () => {
  it('bir tomon javob bermasa ko‘rik yakunlanmaydi; e‘tiroz izoh bilan yuboriladi', async () => {
    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, status: 'ACTIVE', agreement: agreementOf('ACTIVE') }],
    });
    vi.mocked(commands.reviewView).mockResolvedValue({
      status: 'ok',
      data: {
        period: '2026-10',
        closed: false,
        chain_length: 4,
        chain_intact: true,
        broken_seq: null,
        recorded_head: null,
        head_matches: null,
        parties: [
          { party_id: 'a', name: 'Karim aka', agree: true, note: null },
          { party_id: 'b', name: 'Zamira', agree: null, note: null },
        ],
        ledger: [],
        incidents: [],
      },
    });
    renderPage();
    const session = within(await screen.findByTestId('review-session'));
    expect(session.getByRole('button', { name: "Ko'rikni yakunlash" })).toBeDisabled();
    const zamira = within(screen.getByTestId('review-party-Zamira'));
    await userEvent.click(zamira.getByRole('button', { name: "E'tirozim bor" }));
    await userEvent.type(zamira.getByLabelText("E'tiroz izohi"), 'Yo‘l xarajati');
    await userEvent.click(zamira.getByRole('button', { name: "E'tirozni yozish" }));
    await waitFor(() => {
      expect(commands.recordReviewAnswer).toHaveBeenCalledWith(
        'p1',
        expect.stringMatching(/^\d{4}-\d{2}$/),
        'b',
        false,
        'Yo‘l xarajati',
      );
    });
  });

  it('yopilgan ko‘rikda zanjir boshi mos kelmasa, ogohlantirish chiqadi', async () => {
    vi.mocked(commands.listPartnerships).mockResolvedValue({
      status: 'ok',
      data: [{ ...base, status: 'ACTIVE', agreement: agreementOf('ACTIVE') }],
    });
    vi.mocked(commands.reviewView).mockResolvedValue({
      status: 'ok',
      data: {
        period: '2026-10',
        closed: true,
        chain_length: 6,
        chain_intact: true,
        broken_seq: null,
        recorded_head: 'ab12',
        head_matches: false,
        parties: [{ party_id: 'a', name: 'Karim aka', agree: true, note: null }],
        ledger: [],
        incidents: [],
      },
    });
    renderPage();
    expect(await screen.findByTestId('review-head')).toHaveTextContent('MOS KELMAYDI');
  });
});
