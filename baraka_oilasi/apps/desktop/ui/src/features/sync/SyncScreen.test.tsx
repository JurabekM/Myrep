import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { SetupScreen } from "../setup/SetupScreen";
import { SyncScreen } from "./SyncScreen";

const fns = {
  devices: vi.fn(),
  exportBaraka: vi.fn(),
  pickBarakaFile: vi.fn(),
  inspectBaraka: vi.fn(),
  applyBaraka: vi.fn(),
  pairingOffer: vi.fn(),
  joinHousehold: vi.fn(),
  setup: vi.fn(),
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

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

const devices = [
  { id: "dev-desktop", name: "Kompyuter", platform: "linux", pairedAt: "2026-10-15", isThis: true, lastImportAt: null, lastExportAt: null },
  { id: "dev-phone", name: "Nilufarning telefoni", platform: "android", pairedAt: "2026-12-02", isThis: false, lastImportAt: "2026-12-02T09:10:00.000Z", lastExportAt: null },
];

const preview = (over: Record<string, unknown> = {}) => ({
  sourceDeviceId: "dev-phone",
  sourceDeviceName: "Nilufarning telefoni",
  mode: "INCREMENTAL",
  exportedAt: "2026-12-02T09:00:00.000Z",
  rows: 3,
  inserts: 1,
  updates: 0,
  same: 0,
  keptLocal: 0,
  journalAppended: 0,
  protected: [{ key: "venture_periods:p1", table: "venture_periods", rowId: "p1", label: "" }],
  conflicts: [
    {
      key: "categories:c1",
      table: "categories",
      rowId: "c1",
      label: "Oziq-ovqat (D)",
      fields: [{ field: "custom_name", local: "Oziq-ovqat (D)", remote: "Oziq-ovqat (T)" }],
      localDeleted: false,
      remoteDeleted: false,
    },
  ],
  forks: [],
  canApply: true,
  ...over,
});

beforeEach(() => {
  Object.values(fns).forEach((f) => f.mockReset());
  fns.devices.mockResolvedValue(ok(devices));
  fns.pickBarakaFile.mockResolvedValue(ok({ path: "/tmp/x.baraka", name: "x.baraka" }));
});

describe("SyncScreen", () => {
  it("eksport: parollar mos bo'lsin; qurilma uchun inkremental", async () => {
    fns.exportBaraka.mockResolvedValue(ok(4));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    expect(await screen.findByText("Nilufarning telefoni")).toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Eksport" });
    await user.click(within(form).getByLabelText(/Qurilma uchun/));
    const pw = within(form).getByLabelText("Fayl paroli");
    const pw2 = within(form).getByLabelText("Parolni takrorlang");
    await user.type(pw, "Baraka-2026!");
    await user.type(pw2, "Baraka-2026?");
    await user.click(within(form).getByRole("button", { name: "Faylni saqlash" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("Parollar mos kelmadi");
    await user.clear(pw2);
    await user.type(pw2, "Baraka-2026!");
    await user.click(within(form).getByRole("button", { name: "Faylni saqlash" }));
    expect(fns.exportBaraka).toHaveBeenCalledWith({ password: "Baraka-2026!", mode: "INCREMENTAL", peerDeviceId: "dev-phone" });
    expect(await within(form).findByRole("status")).toHaveTextContent("4 ta yozuv");
  });

  it("import: ziddiyat tanlanmaguncha qabul qilinmaydi, yopilgan yozuv ko'rsatiladi", async () => {
    fns.inspectBaraka.mockResolvedValue(ok(preview()));
    fns.applyBaraka.mockResolvedValue(ok({ inserted: 1, updated: 0, conflictsLocal: 0, conflictsRemote: 1, protected: 1, journalAppended: 0 }));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    const section = screen.getByRole("region", { name: "Import" });
    await user.click(within(section).getByRole("button", { name: "Fayl tanlash" }));
    await user.type(await within(section).findByLabelText("Fayl paroli"), "Baraka-2026!");
    await user.click(within(section).getByRole("button", { name: "Koʻrib chiqish" }));
    expect(await within(section).findByText(/Yopilgan davr/)).toBeInTheDocument();
    const conflict = within(section).getByRole("article", { name: "Oziq-ovqat (D)" });
    expect(within(conflict).getByText("Oziq-ovqat (T)")).toBeInTheDocument();
    const apply = within(section).getByRole("button", { name: "Qabul qilish" });
    expect(apply).toBeDisabled();
    await user.click(within(conflict).getByLabelText("Kelgan fayldagisi olinsin"));
    expect(apply).toBeEnabled();
    await user.click(apply);
    expect(fns.applyBaraka).toHaveBeenCalledWith("/tmp/x.baraka", "Baraka-2026!", [{ key: "categories:c1", choice: "REMOTE" }]);
    expect(await within(section).findByRole("status")).toHaveTextContent("1 ta yangi");
  });

  it("ayrilishda import to'xtaydi", async () => {
    fns.inspectBaraka.mockResolvedValue(
      ok(preview({ conflicts: [], protected: [], canApply: false, forks: [{ agreementId: "a1", title: "Tikuvchilik ustaxonasi", seq: 5, reason: "FORK" }] })),
    );
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    const section = screen.getByRole("region", { name: "Import" });
    await user.click(within(section).getByRole("button", { name: "Fayl tanlash" }));
    await user.type(await within(section).findByLabelText("Fayl paroli"), "x");
    await user.click(within(section).getByRole("button", { name: "Koʻrib chiqish" }));
    const alert = await within(section).findByRole("alert");
    expect(alert).toHaveTextContent("«Tikuvchilik ustaxonasi» jurnali 5-yozuvdan boshlab");
    expect(within(section).getByRole("button", { name: "Qabul qilish" })).toBeDisabled();
  });

  it("yangi qurilmani ulash: QR va kod", async () => {
    fns.pairingOffer.mockResolvedValue(ok({ code: "ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ23-4567", qrSvg: "<svg/>", householdName: "Oila", fileName: "ulash.baraka" }));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    await user.click(screen.getByRole("button", { name: "Ulash faylini yaratish" }));
    expect(await screen.findByTestId("pairing-code")).toHaveTextContent("ABCD-EFGH");
    expect(screen.getByAltText("Ulash QR kodi")).toBeInTheDocument();
  });
});

describe("SetupScreen: mavjud xonadonga qo'shilish", () => {
  it("fayl, kod va PIN bilan", async () => {
    fns.joinHousehold.mockResolvedValue(ok({ household: { id: "h1" }, recoveryCode: "AAAA-BBBB" }));
    const user = userEvent.setup();
    wrap(<SetupScreen />);
    await user.click(screen.getByRole("tab", { name: "Mavjud xonadonga qoʻshilish" }));
    expect(screen.queryByLabelText("Oila nomi")).not.toBeInTheDocument();
    const submit = screen.getByRole("button", { name: "Qoʻshilish" });
    expect(submit).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Fayl tanlash" }));
    expect(await screen.findByText("x.baraka")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Ulash kodi yoki zaxira nusxa paroli"), "abcd efgh");
    await user.type(screen.getByLabelText("6 xonali PIN"), "445566");
    await user.type(screen.getByLabelText("PINʼni takrorlang"), "445566");
    await user.click(submit);
    expect(fns.joinHousehold).toHaveBeenCalledWith("/tmp/x.baraka", "445566", { secret: "abcd efgh", deviceName: "Desktop", platform: "desktop" });
    expect(await screen.findByTestId("recovery-code")).toHaveTextContent("AAAA-BBBB");
  });
});
