import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../bindings/bindings";
import { setAppLanguage } from "../i18n";
import { App } from "./App";
import { useUiStore } from "./store";

// Testda haqiqiy Tauri IPC yo'q: get_app_info javobi soxtalashtiriladi.
vi.mock("../bindings/bindings", () => ({
  commands: { getAppInfo: vi.fn() },
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
    // Zustand do'koni modul darajasida: har test bosh sahifadan boshlanishi uchun tiklanadi.
    useUiStore.setState({ page: "home" });
  });

  afterEach(async () => {
    await setAppLanguage("uz");
  });

  it("standart tilda bosh sahifani va ilova ma'lumotini ko'rsatadi", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: UZ_GREETING })).toBeInTheDocument();
    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("windows · x86_64")).toBeInTheDocument();
    expect(screen.getByText("Reliz")).toBeInTheDocument();
  });

  it("faol bo'lmagan bo'lim bosilmaydi va sababi tooltip'da ko'rsatiladi", async () => {
    const user = userEvent.setup();
    render(<App />);

    const incomeButton = screen.getByRole("button", { name: "Daromad" });
    expect(incomeButton).toHaveAttribute("aria-disabled", "true");

    // Avval sabab ko'rinadi (hover), keyin bosish sinaladi: bosilgach tooltip qayta ochilmaydi (Radix xulqi).
    await user.hover(incomeButton);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Bu boʻlim keyingi bosqichda qoʻshiladi",
    );

    await user.click(incomeButton);
    expect(screen.getByRole("heading", { level: 1, name: UZ_GREETING })).toBeInTheDocument();
  });

  it("sozlamalar ochiladi va tilni almashtirish darhol qo'llanadi", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Sozlamalar" }));
    expect(screen.getByRole("heading", { level: 1, name: "Sozlamalar" })).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Русский" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Настройки" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Главная" })).toBeInTheDocument();
  });

  it("yon paneldagi tugma bilan tilni ruscha qilish mumkin", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("radio", { name: "RU" }));

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
