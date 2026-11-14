import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type ImportReportDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// D14 UI: eksport (parol ≥ 8), import ko'rigi → qo'llash; fork — bloklangan; noto'g'ri parol — aniq xabar.
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
    exportBaraka: vi.fn(),
    previewBarakaImport: vi.fn(),
    applyBarakaImport: vi.fn(),
  },
}));

const REPORT: ImportReportDto = {
  blocked: false,
  inserted: [
    { table: "households", count: 1 },
    { table: "agreements", count: 1 },
  ],
  updated: [],
  conflicts: [{ table: "agreements", id: "0192e000-aaaa", reason: "LOCAL_NEWER" }],
  forks: [],
  journalAppended: 2,
  exportedAt: "2026-12-01T06:00:00Z",
  deviceId: "phone",
  householdMismatch: false,
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
}

describe("almashish (.baraka)", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "settings", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("eksport parol bilan yuboriladi va natija ko'rsatiladi", async () => {
    vi.mocked(commands.exportBaraka).mockResolvedValue({
      status: "ok",
      data: { path: "C:\\exports\\baraka-1.baraka", tables: 42, rows: 17 },
    });
    render(<App />);
    const user = userEvent.setup();
    const button = await screen.findByRole("button", { name: "Eksport qilish" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Eksport paroli (kamida 8 belgi)"), "juda-sirli-parol");
    expect(button).toBeEnabled();
    await user.click(button);
    expect(commands.exportBaraka).toHaveBeenCalledWith({
      path: null,
      password: "juda-sirli-parol",
      since: null,
    });
    expect(await screen.findByRole("status")).toHaveTextContent(/baraka-1\.baraka/);
  });

  it("import ko'rigi ziddiyat bilan ko'rsatiladi va qo'llanadi; noto'g'ri parol aniq xabar", async () => {
    vi.mocked(commands.previewBarakaImport)
      .mockResolvedValueOnce({ status: "error", error: { code: "WRONG_PASSWORD" } })
      .mockResolvedValueOnce({ status: "ok", data: REPORT });
    vi.mocked(commands.applyBarakaImport).mockResolvedValue({ status: "ok", data: REPORT });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Fayl yo'li (.baraka)"), "C:\\in\\phone.baraka");
    await user.type(screen.getByLabelText("Import paroli"), "notogri-parol-1");
    await user.click(screen.getByRole("button", { name: "Ko'rib chiqish" }));
    expect(await screen.findByText("Almashish fayli paroli noto'g'ri")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ko'rib chiqish" }));
    const preview = await screen.findByRole("region", { name: "Import ko'rigi" });
    expect(within(preview).getByText(/2 qo'shiladi/)).toBeInTheDocument();
    expect(within(preview).getByText(/LOCAL_NEWER/)).toBeInTheDocument();
    await user.click(within(preview).getByRole("button", { name: "Importni qo'llash" }));
    expect(commands.applyBarakaImport).toHaveBeenCalledWith({
      path: "C:\\in\\phone.baraka",
      password: "notogri-parol-1",
    });
    expect(await screen.findByRole("region", { name: "Import natijasi" })).toBeInTheDocument();
  });

  it("fork bo'lsa import bloklanadi", async () => {
    vi.mocked(commands.previewBarakaImport).mockResolvedValue({
      status: "ok",
      data: {
        ...REPORT,
        blocked: true,
        inserted: [],
        conflicts: [],
        forks: [{ agreementId: "0192e000-bbbb", firstBroken: 3 }],
      },
    });
    render(<App />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Fayl yo'li (.baraka)"), "C:\\in\\phone.baraka");
    await user.type(screen.getByLabelText("Import paroli"), "juda-sirli-parol");
    await user.click(screen.getByRole("button", { name: "Ko'rib chiqish" }));
    const preview = await screen.findByRole("region", { name: "Import ko'rigi" });
    expect(within(preview).getByText(/3-yozuvdan/)).toBeInTheDocument();
    expect(within(preview).queryByRole("button", { name: "Importni qo'llash" })).toBeNull();
    expect(within(preview).getByText(/avtomatik birlashtirilmaydi/)).toBeInTheDocument();
  });
});
