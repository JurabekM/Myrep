import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { useUi } from "../../state/ui";
import { HomeScreen } from "../home/HomeScreen";
import { LedgerView } from "../venture/LedgerView";
import { AgreementsScreen } from "./AgreementsScreen";
import { GovernanceView } from "./GovernanceView";

const fns = {
  ventureLedger: vi.fn(),
  venturePeriodPreview: vi.fn(),
  closeVenturePeriod: vi.fn(),
  acknowledgeSpikeReread: vi.fn(),
  partnership: vi.fn(),
  governance: vi.fn(),
  reviewDraft: vi.fn(),
  holdReview: vi.fn(),
  reportDutyIncident: vi.fn(),
  agreementsCenter: vi.fn(),
  familyAgreements: vi.fn(),
  createFamilyAgreement: vi.fn(),
  confirmFamilyAgreement: vi.fn(),
  agreementReminders: vi.fn(),
  monthlySummary: vi.fn(),
  vault: vi.fn(),
  debtsOverview: vi.fn(),
};
vi.mock("../../bindings", () => ({
  commands: new Proxy(
    {},
    {
      get: (_t, name: string) =>
        (...a: unknown[]) =>
          (fns as Record<string, (...x: unknown[]) => unknown>)[name]?.(...a) ?? new Promise(() => {}),
    },
  ),
}));

const ok = (data: unknown) => ({ status: "ok", data });
const money = (formatted: string, minor: string) => ({ minor, currency: "UZS", formatted, plain: minor });
const zero = money("0 soʻm", "0");

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const ledger = (inDispute: boolean) => ({
  partnershipId: "p1",
  title: "Tikuvchilik ustaxonasi",
  kind: "MUDARABA",
  status: "ACTIVE",
  currency: "UZS",
  writable: true,
  readOnlyReason: null,
  keeperName: "Feruza Karimova",
  startOn: "2026-11-01",
  open: { no: 1, from: "2026-11-01", entries: 2, income: money("20 000 000 soʻm", "2000000000"), expense: money("2 000 000 soʻm", "200000000"), forceMajeure: zero, corrections: zero, result: money("18 000 000 soʻm", "1800000000") },
  entries: [],
  periods: [],
  balances: [
    { partyId: "P1", name: "Otabek Qodirov", role: "CAPITAL_PROVIDER", isMe: false, capital: money("30 000 000 soʻm", "3000000000"), carriedLoss: zero },
    { partyId: "P2", name: "Feruza Karimova", role: "WORKER", isMe: true, capital: zero, carriedLoss: zero },
  ],
  buyout: null,
  chainCode: "AB12-CD34-EF56-7890",
  chainOk: true,
  lossPolicy: "CAPITAL_FIRST",
  inDispute,
});

const preview = (profitSpike: boolean, spikeRereads: string[]) => ({
  id: null,
  no: 1,
  startOn: "2026-11-01",
  endOn: "2026-11-30",
  closedAt: null,
  entries: 2,
  income: zero,
  expense: zero,
  forceMajeure: zero,
  corrections: zero,
  result: money("18 000 000 soʻm", "1800000000"),
  recovered: zero,
  distributable: money("18 000 000 soʻm", "1800000000"),
  parties: [],
  buyout: null,
  lossPolicy: "CAPITAL_FIRST",
  negligentParty: null,
  negligenceNote: null,
  myIncome: zero,
  chainCode: null,
  profitSpike,
  spikeRereads,
});

describe("LedgerView: «katta foyda» va nizo", () => {
  beforeEach(() => {
    fns.partnership.mockResolvedValue(
      ok({
        parties: [
          { id: "P1", fullName: "Otabek Qodirov", profitShare: "50%", lossShare: "100%" },
          { id: "P2", fullName: "Feruza Karimova", profitShare: "50%", lossShare: "0%" },
        ],
        negligenceClause: "Uskunani boshqa ishga berish",
      }),
    );
  });

  it("katta foydada hamma 4–5-bandlarni qayta o'qimaguncha yopib bo'lmaydi", async () => {
    fns.ventureLedger.mockResolvedValue(ok(ledger(false)));
    fns.venturePeriodPreview.mockResolvedValue(ok(preview(true, ["P1"])));
    fns.acknowledgeSpikeReread.mockResolvedValue(ok(ledger(false)));
    const user = userEvent.setup();
    wrap(<LedgerView spaceId="uy" partnershipId="p1" />);
    await user.click(await screen.findByRole("button", { name: "Taqsimotni koʻrish" }));
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("Katta foyda: 18 000 000 soʻm")).toBeInTheDocument();
    expect(await within(alert).findByText("Uskunani boshqa ishga berish")).toBeInTheDocument();
    expect(within(alert).getByText("✓ Otabek Qodirov qayta oʻqidi")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Davrni yopish" })).toBeDisabled();
    await user.click(within(alert).getByRole("button", { name: "Feruza Karimova 4–5-bandlarni qayta oʻqidi" }));
    expect(fns.acknowledgeSpikeReread).toHaveBeenCalledWith("uy", "p1", "P2");
  });

  it("nizo ochiq — taqsimot bloklangan", async () => {
    fns.ventureLedger.mockResolvedValue(ok(ledger(true)));
    fns.venturePeriodPreview.mockResolvedValue(ok(preview(false, [])));
    const user = userEvent.setup();
    wrap(<LedgerView spaceId="uy" partnershipId="p1" />);
    expect(await screen.findByText(/Nizo ochiq: yozuvlar davom etadi/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Taqsimotni koʻrish" }));
    expect(await screen.findByRole("button", { name: "Davrni yopish" })).toBeDisabled();
  });
});

const review = (integrity: string) => ({
  id: "r1",
  no: 1,
  fromOn: "2026-11-01",
  toOn: "2026-12-01",
  reason: "SCHEDULED",
  heldOn: "2026-12-02",
  totals: { entries: 2, periodsClosed: 0, income: zero, expense: zero, forceMajeure: zero, corrections: zero, result: zero },
  openIncidents: 1,
  acks: [
    { partyId: "P1", partyName: "Otabek Qodirov", verdict: "AGREE", note: null },
    { partyId: "P2", partyName: "Feruza Karimova", verdict: "OBJECT", note: "Mato narxi" },
  ],
  chainCode: "A765-1DD8-4DAD-994D",
  integrity,
  entriesAfter: 0,
});

const gov = {
  partnershipId: "p1",
  title: "Tikuvchilik ustaxonasi",
  status: "ACTIVE",
  inDispute: false,
  writable: true,
  readOnlyReason: null,
  parties: [
    { partyId: "P1", name: "Otabek Qodirov" },
    { partyId: "P2", name: "Feruza Karimova" },
  ],
  duties: [{ id: "d1", title: "Buyurtmalarni tikish", ownerPartyId: "P2", ownerName: "Feruza Karimova", breachClause: "1 kun ichida xabar beradi va oʻrniga yechim topadi" }],
  incidents: [],
  reviews: [review("HEAD_MISMATCH")],
  disputes: [],
  arbiterName: "Hamid aka",
  reviewEveryDays: 30,
  nextReviewDue: "2027-01-01",
  reviewReminder: null,
  reviewDate: "2027-11-01",
  renewalReminder: { agreementId: "a1", refId: "p1", agreementType: "PARTNERSHIP", kind: "RENEWAL", title: "Tikuvchilik ustaxonasi", dueOn: "2027-11-01", state: "UPCOMING", days: 22 },
};

describe("GovernanceView", () => {
  it("bayonnoma yaxlitligi, yangilash eslatmasi va «bajara olmayapman»", async () => {
    fns.governance.mockResolvedValue(ok(gov));
    fns.reportDutyIncident.mockResolvedValue(
      ok({
        ...gov,
        incidents: [
          {
            id: "i1",
            dutyId: "d1",
            dutyTitle: "Buyurtmalarni tikish",
            breachClause: "1 kun ichida xabar beradi va oʻrniga yechim topadi",
            partyId: "P2",
            partyName: "Feruza Karimova",
            reason: "Kasal",
            occurredOn: "2026-12-01",
            proposedSolution: null,
            resolvedOn: null,
            resolutionNote: null,
            hashCode: "1111-2222-3333-4444",
          },
        ],
      }),
    );
    const user = userEvent.setup();
    wrap(<GovernanceView spaceId="uy" partnershipId="p1" onOpenContract={() => {}} />);
    expect(await screen.findByText("Bayonnomadagi kod mos emas")).toBeInTheDocument();
    expect(screen.getByText("22 kun qoldi (01.11.2027)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bajara olmayapman" }));
    const form = screen.getByRole("form", { name: "Bajara olmayapman" });
    await user.type(within(form).getByLabelText("Sabab"), "Kasal");
    await user.click(within(form).getByRole("button", { name: "Xabar berish" }));
    expect(fns.reportDutyIncident).toHaveBeenCalledWith("uy", "p1", expect.objectContaining({ dutyId: "d1", partyId: "P2", reason: "Kasal", proposedSolution: null }));
    const status = await screen.findByText(/Xabar jurnalga yozildi/);
    expect(status.parentElement).toHaveTextContent("Kelishuvga koʻra endi: 1 kun ichida xabar beradi va oʻrniga yechim topadi");
  });

  it("ko'rik sessiyasi: har tomon belgisi, e'tiroz izohsiz bo'lmaydi", async () => {
    fns.governance.mockResolvedValue(ok({ ...gov, reviews: [] }));
    fns.reviewDraft.mockResolvedValue(
      ok({
        no: 1,
        fromOn: "2026-11-01",
        toOn: "2026-12-02",
        entries: [],
        totals: { entries: 2, periodsClosed: 0, income: zero, expense: zero, forceMajeure: zero, corrections: zero, result: money("+7 000 000 soʻm", "700000000") },
        openIncidents: [],
        chainOk: true,
        chainCode: "AB12-CD34-EF56-7890",
        chainEntries: 5,
        parties: gov.parties,
      }),
    );
    fns.holdReview.mockResolvedValue(ok(gov));
    const user = userEvent.setup();
    wrap(<GovernanceView spaceId="uy" partnershipId="p1" onOpenContract={() => {}} />);
    await user.click(await screen.findByRole("button", { name: "Koʻrikni boshlash" }));
    const dialog = screen.getByRole("dialog", { name: "Ochiq hisob koʻrigi" });
    expect(await within(dialog).findByText("Zanjir tekshiruvi: barcha yozuvlar butun.")).toBeInTheDocument();
    expect(fns.reviewDraft).toHaveBeenCalledWith("uy", "p1", "");
    const hold = within(dialog).getByRole("button", { name: "Bayonnomani yozish" });
    expect(hold).toBeDisabled();
    await user.click(within(within(dialog).getByRole("radiogroup", { name: "Otabek Qodirov" })).getByLabelText("Koʻrdim, roziman"));
    await user.click(within(within(dialog).getByRole("radiogroup", { name: "Feruza Karimova" })).getByLabelText("Eʼtirozim bor"));
    expect(hold).toBeDisabled();
    await user.type(within(dialog).getByLabelText("Feruza Karimova: eʼtiroz mazmuni"), "Mato narxi");
    expect(hold).toBeEnabled();
    await user.click(hold);
    expect(fns.holdReview).toHaveBeenCalledWith(
      "uy",
      "p1",
      expect.objectContaining({
        toOn: "2026-12-02",
        reason: "SCHEDULED",
        acks: [
          { partyId: "P1", verdict: "AGREE", note: null },
          { partyId: "P2", verdict: "OBJECT", note: "Mato narxi" },
        ],
      }),
    );
  });
});

describe("AgreementsScreen", () => {
  const center = [
    { agreementId: "a1", agreementType: "PARTNERSHIP", refId: "p1", title: "Tikuvchilik ustaxonasi", status: "IN_DISPUTE", nextReview: "2027-01-01", reminder: null, openIncidents: 1, openDisputes: 1 },
    { agreementId: "a2", agreementType: "FAMILY", refId: "a2", title: "Uy yumushlari", status: "ACTIVE", nextReview: "2027-03-01", reminder: null, openIncidents: 0, openDisputes: 0 },
    { agreementId: "a3", agreementType: "LOAN", refId: "a3", title: "Qoʻshniga qarz", status: "DRAFT", nextReview: null, reminder: null, openIncidents: 0, openDisputes: 0 },
  ];

  it("jadval: tur bo'yicha filtr va qidiruv", async () => {
    fns.agreementsCenter.mockResolvedValue(ok(center));
    const user = userEvent.setup();
    wrap(<AgreementsScreen spaceId="uy" />);
    expect(await screen.findByText("Tikuvchilik ustaxonasi")).toBeInTheDocument();
    expect(screen.getByText("Nizoda")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Turi boʻyicha"), "FAMILY");
    expect(screen.queryByText("Tikuvchilik ustaxonasi")).not.toBeInTheDocument();
    expect(screen.getByText("Uy yumushlari")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Turi boʻyicha"), "ALL");
    await user.type(screen.getByLabelText("Qidirish"), "qarz");
    expect(screen.getByText("Qoʻshniga qarz")).toBeInTheDocument();
    expect(screen.queryByText("Uy yumushlari")).not.toBeInTheDocument();
  });

  it("oilaviy kelishuv: shablondan yaratish va PIN bilan tasdiq", async () => {
    fns.agreementsCenter.mockResolvedValue(ok([]));
    fns.familyAgreements.mockResolvedValue(
      ok([
        {
          id: "f1",
          templateKey: "CHORES",
          title: "Uyda kim nima qiladi",
          items: ["Idish — navbat bilan"],
          reviewDate: null,
          status: "DRAFT",
          adults: [
            { memberId: "m1", name: "Feruza", agreedOn: "2026-12-02" },
            { memberId: "m2", name: "Bobur", agreedOn: null },
          ],
          hashCode: "AAAA-BBBB-CCCC-DDDD",
        },
      ]),
    );
    fns.createFamilyAgreement.mockResolvedValue(ok({}));
    fns.confirmFamilyAgreement.mockResolvedValue(ok({}));
    const user = userEvent.setup();
    wrap(<AgreementsScreen spaceId="uy" />);
    await user.click(screen.getByRole("tab", { name: "Oilaviy kelishuvlar" }));
    expect(await screen.findByText("Tasdiq kutilmoqda")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bobur tasdiqlaydi" }));
    await user.type(screen.getByLabelText("Bobur: PIN bilan tasdiqlang"), "123456");
    await user.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    expect(fns.confirmFamilyAgreement).toHaveBeenCalledWith("uy", "123456", "f1", "m2");

    await user.click(screen.getByRole("button", { name: "Pul qayerda turadi va kim yuritadi" }));
    const form = screen.getByRole("form", { name: "Oilaviy kelishuv" });
    expect(within(form).getByLabelText("1-band")).toHaveValue("Oylik xarajat puli — umumiy kartada");
    await user.click(within(form).getByRole("button", { name: "Saqlash" }));
    expect(fns.createFamilyAgreement).toHaveBeenCalledWith("uy", expect.objectContaining({ templateKey: "MONEY_PLACE", title: "Pul qayerda turadi va kim yuritadi", reviewDate: null }));
  });
});

describe("HomeScreen: kelishuv eslatmalari", () => {
  it("yangilash eslatmasi sheriklikning «Ko'rik va nizo» bo'limini ochadi", async () => {
    fns.monthlySummary.mockResolvedValue(ok({ paidToSelf: zero, monthResult: zero }));
    fns.vault.mockResolvedValue(ok({ balance: zero, streak: { currentWeeks: 0 } }));
    fns.debtsOverview.mockResolvedValue(ok({ debtFreeDate: null }));
    fns.agreementReminders.mockResolvedValue(ok([gov.renewalReminder]));
    const user = userEvent.setup();
    wrap(<HomeScreen spaceId="uy" />);
    const card = await screen.findByRole("region", { name: "Kelishuv eslatmalari" });
    expect(within(card).getByText("Yillik yangilash")).toBeInTheDocument();
    await user.click(within(card).getByRole("button"));
    expect(useUi.getState().screen).toBe("partnerships");
    expect(useUi.getState().partnershipFocus).toEqual({ id: "p1", tab: "governance" });
  });
});
