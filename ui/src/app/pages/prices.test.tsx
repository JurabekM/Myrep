import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type PricesDto, type ReserveDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { tenthsText } from "../finance/ReserveCard";
import { useUiStore } from "../store";
import { bpText } from "./PricesPage";

// D8 UI: zaxira kartasi (Kelajagim) va Narx daftari. Raqamlar backend'dan tayyor keladi.
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
    getReserve: vi.fn(),
    getPrices: vi.fn(),
    addPriceItem: vi.fn(),
    updatePrice: vi.fn(),
    removePriceItem: vi.fn(),
  },
}));

const RESERVE: ReserveDto = {
  balance: money(400_000_000, "4 000 000 soʻm"),
  monthlyAverage: money(300_000_000, "3 000 000 soʻm"),
  targetFirst: money(900_000_000, "9 000 000 soʻm"),
  targetFull: money(1_800_000_000, "18 000 000 soʻm"),
  reserveMonthsTenths: 13,
  targetMonths: 6,
  gate: "LOCKED",
  reasons: ["RESERVE_BELOW_TARGET"],
  dataMonths: 3,
};

const PRICES: PricesDto = {
  items: [
    {
      id: "0192e000-0000-7000-8000-0000000000f1",
      name: "go'sht, 1 kg",
      basePrice: money(8_000_000, "80 000 soʻm"),
      currentPrice: money(13_000_000, "130 000 soʻm"),
      weightBp: 5000,
      changeBp: 6250,
    },
  ],
  indexBp: 6250,
  balance: money(400_000_000, "4 000 000 soʻm"),
  realValue: money(246_153_846, "2 461 538,46 soʻm"),
  exampleName: "go'sht, 1 kg",
  exampleUnitsBefore: 50,
  exampleUnitsNow: 30,
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue({
    name: "Baraka Dastur",
    version: "0.1.0",
    platform: "windows",
    arch: "x86_64",
    buildProfile: "release",
  });
  vi.mocked(commands.getSecurityStatus).mockResolvedValue({
    status: "ok",
    data: { setUp: true, unlocked: true },
  });
  resetFinanceMocks();
  vi.mocked(commands.getReserve).mockResolvedValue({ status: "ok", data: RESERVE });
  vi.mocked(commands.getPrices).mockResolvedValue({ status: "ok", data: PRICES });
}

describe("zaxira va narx daftari", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("formatlash yordamchilari", () => {
    expect(tenthsText(13)).toBe("1,3");
    expect(tenthsText(60)).toBe("6,0");
    expect(bpText(6250)).toBe("+62,5 %");
    expect(bpText(-1000)).toBe("−10,0 %");
    expect(bpText(0)).toBe("0,0 %");
  });

  it("Kelajagim'da zaxira progressi va yopiq darvoza sababi ko'rinadi", async () => {
    useUiStore.setState({ page: "future" });
    render(<App />);
    expect(await screen.findByText("1,3 / 6 oy")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "22");
    expect(screen.getByText("Favqulodda zaxira 6 oydan kam.")).toBeInTheDocument();
    expect(screen.getByText("18 000 000 soʻm")).toBeInTheDocument();
  });

  it("Narx daftari: indeks, real qiymat, misol va yozuv qo'shish", async () => {
    const added: PricesDto = {
      ...PRICES,
      items: [
        ...PRICES.items,
        {
          id: "0192e000-0000-7000-8000-0000000000f2",
          name: "non",
          basePrice: money(200_000, "2 000 soʻm"),
          currentPrice: money(300_000, "3 000 soʻm"),
          weightBp: 1000,
          changeBp: 5000,
        },
      ],
    };
    vi.mocked(commands.addPriceItem).mockResolvedValue({ status: "ok", data: added });
    useUiStore.setState({ page: "prices" });
    render(<App />);
    expect(await screen.findByText("+62,5 %")).toBeInTheDocument();
    expect(screen.getByText("2 461 538,46 soʻm")).toBeInTheDocument();
    expect(
      screen.getByText("go'sht, 1 kg: avval 50 dona olish mumkin edi, hozir — 30 dona."),
    ).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Mahsulot (masalan, go'sht, 1 kg)"), "non");
    await user.type(screen.getByLabelText("Bazaviy narx"), "2 000");
    await user.type(screen.getByLabelText("Joriy narx"), "3 000");
    await user.click(screen.getByRole("button", { name: "Qo'shish" }));
    expect(await screen.findByText("non")).toBeInTheDocument();
    expect(commands.addPriceItem).toHaveBeenCalledWith({
      name: "non",
      basePrice: "2 000",
      currentPrice: "3 000",
      weightBp: 1000,
    });
  });
});
