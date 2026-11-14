import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type HavasLimitDto,
  type MemberDto,
  type TreatDto,
  commands,
} from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Oila va havas oqimlari: IPC soxtalashtiriladi, ko'rinish va o'zaro ta'sir haqiqiy komponentlarda sinaladi.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
    lock: vi.fn(),
    getHome: vi.fn(),
    listIncomesThisMonth: vi.fn(),
    listRecentIncomes: vi.fn(),
    getVault: vi.fn(),
    getAudit: vi.fn(),
    getWhoseMoney: vi.fn(),
    listCategories: vi.fn(),
    listObligations: vi.fn(),
    listDebts: vi.fn(),
    listChapters: vi.fn(),
    getWeeklyTasks: vi.fn(),
    getMonthSummary: vi.fn(),
    listMonthExpenses: vi.fn(),
    addExpense: vi.fn(),
    setCategoryNecessity: vi.fn(),
    getHavasLimit: vi.fn(),
    setHavasLimit: vi.fn(),
    consentHavasLimit: vi.fn(),
    listMembers: vi.fn(),
    addMember: vi.fn(),
    setMemberPin: vi.fn(),
    listTreats: vi.fn(),
    addTreat: vi.fn(),
    addExpenses: vi.fn(),
    listHabits: vi.fn(),
    addHabit: vi.fn(),
    createCouncilReport: vi.fn(),
  },
}));

const APP_INFO = {
  name: "Baraka Dastur",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const OWNER = "0192e000-0000-7000-8000-0000000000a1";
const SPOUSE = "0192e000-0000-7000-8000-0000000000a2";
const SNACKS = "0192e000-0000-7000-8000-0000000000c3";

const SUMMARY = {
  periodStart: "2026-10-01",
  periodEnd: "2026-11-01",
  weekStart: "2026-10-09",
  today: "2026-10-15",
  zarur: money(0, "0 soʻm"),
  kerak: money(0, "0 soʻm"),
  havas: money(0, "0 soʻm"),
  sadaqa: money(0, "0 soʻm"),
  gifts: money(0, "0 soʻm"),
  ostentation: money(0, "0 soʻm"),
  fundedByDebt: money(0, "0 soʻm"),
};

const LIMIT_INACTIVE: HavasLimitDto = {
  limit: money(100_000_000, "1 000 000 soʻm"),
  spent: money(0, "0 soʻm"),
  level: "OK",
  active: false,
  adults: [
    { memberId: OWNER, name: "O'zim", consented: false, hasPin: true },
    { memberId: SPOUSE, name: "Jasur", consented: false, hasPin: true },
  ],
};

const MEMBERS: MemberDto[] = [
  { id: OWNER, name: "O'zim", role: "ADULT", hasPin: true },
  { id: SPOUSE, name: "Jasur", role: "ADULT", hasPin: true },
];

const TREAT: TreatDto = {
  id: "0192e000-0000-7000-8000-0000000000d1",
  name: "Juma shirinligi",
  amount: money(5_000_000, "50 000 soʻm"),
  weekday: 4,
  dueToday: true,
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
  vi.mocked(commands.getSecurityStatus).mockResolvedValue({
    status: "ok",
    data: { setUp: true, unlocked: true },
  });
  resetFinanceMocks();
  vi.mocked(commands.getMonthSummary).mockResolvedValue({ status: "ok", data: SUMMARY });
  vi.mocked(commands.listMonthExpenses).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getHavasLimit).mockResolvedValue({ status: "ok", data: LIMIT_INACTIVE });
  vi.mocked(commands.listMembers).mockResolvedValue({ status: "ok", data: MEMBERS });
  vi.mocked(commands.listTreats).mockResolvedValue({ status: "ok", data: [TREAT] });
  vi.mocked(commands.addExpense).mockResolvedValue({
    status: "ok",
    data: {
      id: "0192e000-0000-7000-8000-0000000000e1",
      occurredOn: "2026-10-15",
      amount: money(15_000_000, "150 000 soʻm"),
      categoryName: null,
      necessity: "KERAK",
      note: null,
      isGift: true,
      isOstentation: false,
      fundedByDebt: false,
    },
  });
  vi.mocked(commands.setCategoryNecessity).mockResolvedValue({
    status: "ok",
    data: { id: SNACKS, name: "Gazak va ichimlik", systemKey: "SNACKS", necessity: "HAVAS" },
  });
  vi.mocked(commands.consentHavasLimit).mockResolvedValue({ status: "ok", data: LIMIT_INACTIVE });
  vi.mocked(commands.addTreat).mockResolvedValue({ status: "ok", data: TREAT });
  vi.mocked(commands.listHabits).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.addExpenses).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.createCouncilReport).mockResolvedValue({
    status: "ok",
    data: "/data/reports/bayonnoma.pdf",
  });
}

/** Birinchi kattaning «Rozilik berish» tugmasi. */
function firstConsentButton(): HTMLElement {
  const [first] = screen.getAllByRole("button", { name: "Rozilik berish" });
  if (first === undefined) {
    throw new Error("Rozilik tugmasi topilmadi");
  }
  return first;
}

/** Birinchi kattaning PIN maydoni (birinchi qator). */
function firstAdultPin(): HTMLElement {
  const [first] = screen.getAllByLabelText("PIN");
  if (first === undefined) {
    throw new Error("PIN maydoni topilmadi");
  }
  return first;
}

async function openExpenses(): Promise<void> {
  useUiStore.setState({ page: "expenses" });
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Xarajatlar" });
}

describe("oila va havas", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("xarajat sovg'a belgisi bilan yoziladi va backend'ga yuboriladi", async () => {
    const user = userEvent.setup();
    await openExpenses();

    await user.type(screen.getByLabelText("Summa", { selector: "#expense-amount" }), "150000");
    await user.click(screen.getByLabelText("Sovg'a (hisobga kirmaydi)"));
    await user.click(screen.getByRole("button", { name: "Saqlash" }));

    expect(commands.addExpense).toHaveBeenCalledWith({
      amount: "150000",
      categoryId: null,
      note: null,
      isGift: true,
      isOstentation: false,
      fundedByDebt: false,
      occurredOn: null,
    });
  });

  it("oy xulosasida sadaqa va havas alohida ko'rsatiladi", async () => {
    await openExpenses();

    expect(await screen.findByText("Sadaqa")).toBeInTheDocument();
    expect(screen.getByText("Sovg'alar va sadaqa havas hisobiga kirmaydi")).toBeInTheDocument();
  });

  it("kengash: toifa o'zgartiriladi va backend'ga yuboriladi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.listCategories).mockResolvedValue({
      status: "ok",
      data: [{ id: SNACKS, name: "Gazak va ichimlik", systemKey: "SNACKS", necessity: "HAVAS" }],
    });
    await openExpenses();

    await user.click(screen.getByRole("button", { name: "Oila kengashi" }));
    await screen.findByRole("dialog", { name: "Oila kengashi" });
    await user.click(screen.getByRole("button", { name: "Keyingi" }));

    const select = await screen.findByRole("combobox", {
      name: "Gazak va ichimlik: Toifa",
    });
    await user.selectOptions(select, "KERAK");

    await waitFor(() => {
      expect(commands.setCategoryNecessity).toHaveBeenCalledWith(SNACKS, "KERAK");
    });
  });

  it("havas chegarasi: faqat bitta katta rozi bo'lsa — chegara faol emas, rozilik PIN bilan yuboriladi", async () => {
    const user = userEvent.setup();
    await openExpenses();

    await user.click(screen.getByRole("button", { name: "Oila kengashi" }));
    await screen.findByRole("dialog", { name: "Oila kengashi" });
    await user.click(screen.getByRole("button", { name: "Keyingi" }));
    await user.click(screen.getByRole("button", { name: "Keyingi" }));

    expect(
      await screen.findByText("Chegara faol emas: barcha kattalar rozi bo'lishi kerak."),
    ).toBeInTheDocument();

    await user.type(firstAdultPin(), "123456");
    await user.click(firstConsentButton());

    expect(commands.consentHavasLimit).toHaveBeenCalledWith(OWNER, "123456");
  });

  it("noto'g'ri PIN: xato matni ko'rsatiladi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.consentHavasLimit).mockResolvedValue({
      status: "error",
      error: { code: "WRONG_PIN" },
    });
    await openExpenses();

    await user.click(screen.getByRole("button", { name: "Oila kengashi" }));
    await screen.findByRole("dialog", { name: "Oila kengashi" });
    await user.click(screen.getByRole("button", { name: "Keyingi" }));
    await user.click(screen.getByRole("button", { name: "Keyingi" }));

    await user.type(firstAdultPin(), "000000");
    await user.click(firstConsentButton());

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("juma shirinligi: bugun kuni belgisi va qo'shish", async () => {
    const user = userEvent.setup();
    await openExpenses();

    expect(await screen.findByText("Bugun")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Nomi"), "Shirinlik");
    await user.type(screen.getByLabelText("Summa", { selector: "#treat-amount" }), "20000");
    await user.click(screen.getByRole("button", { name: "Qo'shish" }));

    expect(commands.addTreat).toHaveBeenCalledWith({
      name: "Shirinlik",
      amount: "20000",
      weekday: 4,
    });
  });

  it("Escape kengashni yopadi", async () => {
    const user = userEvent.setup();
    await openExpenses();

    await user.click(screen.getByRole("button", { name: "Oila kengashi" }));
    await screen.findByRole("dialog", { name: "Oila kengashi" });
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog", { name: "Oila kengashi" })).not.toBeInTheDocument();
  });
  it("hafta varag'i: qator sana bilan saqlanadi", async () => {
    const user = userEvent.setup();
    await openExpenses();

    const heading = await screen.findByRole("heading", { level: 2, name: "Hafta varag'i" });
    const card = heading.parentElement;
    if (card === null) {
      throw new Error("Hafta varag'i kartasi topilmadi");
    }
    const [amount] = within(card).getAllByRole("textbox");
    if (amount === undefined) {
      throw new Error("Summa maydoni topilmadi");
    }
    await user.type(amount, "45000");
    await user.click(within(card).getByRole("button", { name: "Hammasini saqlash" }));

    expect(commands.addExpenses).toHaveBeenCalledWith([
      {
        amount: "45000",
        categoryId: null,
        note: null,
        isGift: false,
        isOstentation: false,
        fundedByDebt: false,
        occurredOn: "2026-10-15",
      },
    ]);
  });

  it("odatlar: yangi odat qo'shiladi (statistika)", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.addHabit).mockResolvedValue({
      status: "ok",
      data: {
        id: "0192e000-0000-7000-8000-0000000000f1",
        name: "Chekish",
        monthly: money(0, "0 soʻm"),
        yearly: money(0, "0 soʻm"),
        entriesThisYear: 0,
      },
    });
    await openExpenses();

    await user.type(await screen.findByLabelText("Odat nomi (masalan, chekish)"), "Chekish");
    await user.click(screen.getByRole("button", { name: "Odat qo'shish" }));

    expect(commands.addHabit).toHaveBeenCalledWith("Chekish");
  });

  it("protokol: PDF yaratiladi va yo'li ko'rsatiladi", async () => {
    const user = userEvent.setup();
    await openExpenses();

    await user.click(screen.getByRole("button", { name: "Oila kengashi" }));
    await screen.findByRole("dialog", { name: "Oila kengashi" });
    await user.click(screen.getByRole("button", { name: "Keyingi" }));
    await user.click(screen.getByRole("button", { name: "Keyingi" }));
    await user.click(screen.getByRole("button", { name: "Keyingi" }));
    await user.click(screen.getByRole("button", { name: "Bayonnomani PDF qilish" }));

    expect(
      await screen.findByText(/Bayonnoma saqlandi: \/data\/reports\/bayonnoma\.pdf/),
    ).toBeInTheDocument();
    expect(commands.createCouncilReport).toHaveBeenCalled();
  });
});
