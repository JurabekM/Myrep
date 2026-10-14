import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../bindings/bindings";
import { setAppLanguage } from "../i18n";
import { resetFinanceMocks } from "../test/fixtures";
import { App } from "./App";
import { useUiStore } from "./store";

// Testda haqiqiy Tauri IPC yo'q: commandlar javobi soxtalashtiriladi.
vi.mock("../bindings/bindings", () => ({
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
  },
}));

const APP_INFO = {
  name: "Baraka Daftari",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const UZ_GREETING = "Assalomu alaykum!";

describe("Baraka daftari ilova qobig'i", () => {
  beforeEach(() => {
    vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
    // PIN o'rnatilgan va baza ochiq: asosiy ilova ko'rinadi.
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "ok",
      data: { setUp: true, unlocked: true },
    });
    resetFinanceMocks();
    // Zustand do'koni modul darajasida: har test bosh sahifadan boshlanishi uchun tiklanadi.
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    await setAppLanguage("uz");
  });

  it("standart tilda bosh sahifani va ilova ma'lumotini ko'rsatadi", async () => {
    render(<App />);

    // Xavfsizlik darvozasi holatni avval yuklaydi: asosiy ekran asinxron chiqadi.
    expect(await screen.findByRole("heading", { level: 1, name: UZ_GREETING })).toBeInTheDocument();
    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("windows · x86_64")).toBeInTheDocument();
    expect(screen.getByText("Reliz")).toBeInTheDocument();
  });

  it("faol bo'lmagan bo'lim bosilmaydi va sababi tooltip'da ko'rsatiladi", async () => {
    const user = userEvent.setup();
    render(<App />);

    // «Xarajatlar» hali tayyor emas (D6); «Daromad» endi ochiq.
    const expensesButton = await screen.findByRole("button", { name: "Xarajatlar" });
    expect(expensesButton).toHaveAttribute("aria-disabled", "true");

    // Avval sabab ko'rinadi (hover), keyin bosish sinaladi: bosilgach tooltip qayta ochilmaydi (Radix xulqi).
    await user.hover(expensesButton);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Bu boʻlim keyingi bosqichda qoʻshiladi",
    );

    await user.click(expensesButton);
    expect(screen.getByRole("heading", { level: 1, name: UZ_GREETING })).toBeInTheDocument();
  });

  it("sozlamalar ochiladi va tilni almashtirish darhol qo'llanadi", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Sozlamalar" }));
    expect(screen.getByRole("heading", { level: 1, name: "Sozlamalar" })).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Русский" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Настройки" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Главная" })).toBeInTheDocument();
  });

  it("yon paneldagi tugma bilan tilni ruscha qilish mumkin", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("radio", { name: "RU" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "Ассаламу алейкум!" }),
    ).toBeInTheDocument();
  });

  it("ma'lumot olinmasa, xato xabari ko'rsatiladi", async () => {
    vi.mocked(commands.getAppInfo).mockRejectedValueOnce(new Error("IPC uzildi"));
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Ilova maʼlumotini olib boʻlmadi");
  });
});
