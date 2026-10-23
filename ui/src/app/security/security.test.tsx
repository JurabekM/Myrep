import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../../bindings/bindings";
import uz from "../../i18n/locales/uz/common.json";
import { setAppLanguage } from "../../i18n";
import { resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Testda haqiqiy Tauri IPC yo'q: xavfsizlik va moliya commandlari javobi soxtalashtiriladi.
vi.mock("../../bindings/bindings", () => ({
  commands: {
    getAppInfo: vi.fn(),
    getSecurityStatus: vi.fn(),
    setupPin: vi.fn(),
    unlock: vi.fn(),
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
  },
}));

const APP_INFO = {
  name: "Baraka Dastur",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const GREETING = uz.home.greeting;
const LOCKED_TITLE = uz.security.lockedTitle;
const PIN = "123456";

function status(setUp: boolean, unlocked: boolean) {
  return { status: "ok" as const, data: { setUp, unlocked } };
}

describe("xavfsizlik darvozasi", () => {
  beforeEach(() => {
    vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
    resetFinanceMocks();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    await setAppLanguage("uz");
  });

  it("PIN o'rnatilmagan bo'lsa, sozlash ekrani chiqadi va PIN ikki marta tekshiriladi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.getSecurityStatus)
      .mockResolvedValueOnce(status(false, false))
      .mockResolvedValue(status(true, true));
    vi.mocked(commands.setupPin).mockResolvedValue({ status: "ok", data: null });

    render(<App />);
    expect(
      await screen.findByRole("heading", { level: 1, name: uz.security.setupTitle }),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText(uz.security.pinLabel), PIN);
    await user.type(screen.getByLabelText(uz.security.confirmLabel), "654321");
    await user.click(screen.getByRole("button", { name: uz.security.setupButton }));

    expect(await screen.findByRole("alert")).toHaveTextContent(uz.security.mismatch);
    expect(commands.setupPin).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(uz.security.confirmLabel), PIN);
    await user.click(screen.getByRole("button", { name: uz.security.setupButton }));

    expect(commands.setupPin).toHaveBeenCalledWith(PIN);
    expect(await screen.findByRole("heading", { level: 1, name: GREETING })).toBeInTheDocument();
  });

  it("qulflangan holatda noto'g'ri PIN xabar beradi, to'g'ri PIN ilovani ochadi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.getSecurityStatus)
      .mockResolvedValueOnce(status(true, false))
      .mockResolvedValue(status(true, true));
    vi.mocked(commands.unlock)
      .mockResolvedValueOnce({ status: "error", error: { code: "WRONG_PIN" } })
      .mockResolvedValueOnce({ status: "ok", data: null });

    render(<App />);
    expect(
      await screen.findByRole("heading", { level: 1, name: LOCKED_TITLE }),
    ).toBeInTheDocument();

    const field = screen.getByLabelText(uz.security.pinLabel);
    await user.type(field, "654321{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent(uz.security.wrongPin);
    expect(commands.unlock).toHaveBeenLastCalledWith("654321");

    await user.type(screen.getByLabelText(uz.security.pinLabel), `${PIN}{Enter}`);
    expect(await screen.findByRole("heading", { level: 1, name: GREETING })).toBeInTheDocument();
    expect(commands.unlock).toHaveBeenLastCalledWith(PIN);
  });

  it("juda ko'p urinishda kutish sanog'i chiqadi va maydon o'chiq bo'ladi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.getSecurityStatus).mockResolvedValue(status(true, false));
    vi.mocked(commands.unlock).mockResolvedValue({
      status: "error",
      error: { code: "LOCKED_OUT", retryAfterSeconds: 30 },
    });

    render(<App />);
    await user.type(await screen.findByLabelText(uz.security.pinLabel), `${PIN}{Enter}`);

    expect(await screen.findByRole("alert")).toHaveTextContent("30");
    expect(screen.getByLabelText(uz.security.pinLabel)).toBeDisabled();
    expect(screen.getByRole("button", { name: uz.security.unlock })).toBeDisabled();
  });

  it("Ctrl+L daftarni qulflaydi va qulflash ekrani chiqadi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.getSecurityStatus)
      .mockResolvedValueOnce(status(true, true))
      .mockResolvedValue(status(true, false));
    vi.mocked(commands.lock).mockResolvedValue({ status: "ok", data: null });

    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: GREETING })).toBeInTheDocument();

    await user.keyboard("{Control>}l{/Control}");

    expect(commands.lock).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByRole("heading", { level: 1, name: LOCKED_TITLE }),
    ).toBeInTheDocument();
  });

  it("yon paneldagi «Qulflash» tugmasi ham daftarni qulflaydi", async () => {
    const user = userEvent.setup();
    vi.mocked(commands.getSecurityStatus)
      .mockResolvedValueOnce(status(true, true))
      .mockResolvedValue(status(true, false));
    vi.mocked(commands.lock).mockResolvedValue({ status: "ok", data: null });

    render(<App />);
    await user.click(await screen.findByRole("button", { name: uz.security.lock }));

    expect(commands.lock).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByRole("heading", { level: 1, name: LOCKED_TITLE }),
    ).toBeInTheDocument();
  });

  it("holat olinmasa, xato xabari ko'rsatiladi", async () => {
    vi.mocked(commands.getSecurityStatus).mockResolvedValue({
      status: "error",
      error: { code: "INTERNAL" },
    });

    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(uz.security.statusError);
  });
});
