import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// D15: onboarding ≤ 5 qadam, klaviatura (Esc), «O'tkazib yuborish», bo'limga o'tish; skip-link.
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
  },
}));

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue({
    name: "Baraka Daftari",
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
}

describe("onboarding", () => {
  beforeEach(() => {
    setUp();
    localStorage.removeItem("baraka.onboarding");
    useUiStore.setState({ page: "home", quickEntryOpen: false, onboardingDone: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    localStorage.setItem("baraka.onboarding", "done");
    useUiStore.setState({ onboardingDone: true });
    await setAppLanguage("uz");
  });

  it("5 qadam, oxirida «Boshlash» yopadi va holat saqlanadi", async () => {
    render(<App />);
    const user = userEvent.setup();
    const dialog = await screen.findByRole("dialog", { name: "Xush kelibsiz" });
    expect(within(dialog).getByText("1 / 5")).toBeInTheDocument();
    for (let i = 0; i < 4; i += 1) {
      await user.click(within(dialog).getByRole("button", { name: "Keyingi" }));
    }
    expect(within(dialog).getByText("5 / 5")).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { level: 1 })).toHaveTextContent(
      "Xavfsizlik va telefon",
    );
    await user.click(within(dialog).getByRole("button", { name: "Boshlash" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(localStorage.getItem("baraka.onboarding")).toBe("done");
  });

  it("«Daromad kiritish» bo'limga o'tkazadi; Esc o'tkazib yuboradi; skip-link asosiy mazmunga olib boradi", async () => {
    render(<App />);
    const user = userEvent.setup();
    const dialog = await screen.findByRole("dialog", { name: "Xush kelibsiz" });
    await user.click(within(dialog).getByRole("button", { name: "Keyingi" }));
    await user.click(within(dialog).getByRole("button", { name: "Daromad kiritish" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(useUiStore.getState().page).toBe("income");

    useUiStore.setState({ onboardingDone: false });
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();

    const skip = screen.getByRole("link", { name: "Asosiy mazmunga o'tish" });
    expect(skip).toHaveAttribute("href", "#main");
    expect(document.getElementById("main")).not.toBeNull();
  });
});
