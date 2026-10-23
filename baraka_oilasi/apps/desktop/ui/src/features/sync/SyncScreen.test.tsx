import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { SyncScreen } from "./SyncScreen";

const fns = {
  devices: vi.fn(),
  exportBaraka: vi.fn(),
  pickBarakaFile: vi.fn(),
  inspectBaraka: vi.fn(),
  applyBaraka: vi.fn(),
  pairingOffer: vi.fn(),
  deviceRole: vi.fn(),
  household: vi.fn(),
  revokeDevice: vi.fn(),
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
  { id: "dev-desktop", name: "Kompyuter", platform: "linux", pairedAt: "2026-10-15", isThis: true, lastImportAt: null, lastExportAt: null, role: null, spaceId: null, revoked: false },
  { id: "dev-phone", name: "Feruzaning telefoni", platform: "android", pairedAt: "2026-12-02", isThis: false, lastImportAt: "2026-12-02T09:10:00.000Z", lastExportAt: null, role: null, spaceId: null, revoked: false },
];

const shop = { id: "dev-shop", name: "Do'kon telefoni", platform: "android", pairedAt: "2026-12-02", isThis: false, lastImportAt: null, lastExportAt: null, role: "SELLER", spaceId: "kk", revoked: false };

const preview = (over: Record<string, unknown> = {}) => ({
  sourceDeviceId: "dev-phone",
  sourceDeviceName: "Feruzaning telefoni",
  mode: "INCREMENTAL",
  exportedAt: "2026-12-02T09:00:00.000Z",
  rows: 3,
  inserts: 1,
  updates: 0,
  same: 0,
  keptLocal: 0,
  journalAppended: 0,
  protected: [{ key: "venture_periods:p1", table: "venture_periods", rowId: "p1", label: "" }],
  rejected: [],
  ignored: 0,
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
  fns.deviceRole.mockResolvedValue(ok({ role: "OWNER", spaceId: null, spaceName: null }));
  fns.household.mockResolvedValue(
    ok({ id: "h", name: "Oila", locale: "uz", baseCurrency: "UZS", monthStartDay: 1, members: [], spaces: [{ id: "uy", kind: "UY", name: "Uy" }, { id: "kk", kind: "KASBKOR", name: "Do'kon" }, { id: "mf", kind: "MUSOFIR", name: "Musofir" }] }),
  );
  fns.pickBarakaFile.mockResolvedValue(ok({ path: "/tmp/x.baraka", name: "x.baraka" }));
});

describe("SyncScreen", () => {
  it("eksport: parollar mos bo'lsin; qurilma uchun inkremental", async () => {
    fns.exportBaraka.mockResolvedValue(ok(4));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    expect(await screen.findByText("Feruzaning telefoni")).toBeInTheDocument();
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
    fns.applyBaraka.mockResolvedValue(ok({ inserted: 1, updated: 0, conflictsLocal: 0, conflictsRemote: 1, protected: 1, journalAppended: 0, rejected: 0, ignored: 0 }));
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

  it("K8: sotuvchi qurilmasini ulash — rol va biznes makoni bilan", async () => {
    fns.pairingOffer.mockResolvedValue(ok({ code: "ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ23-4567", qrSvg: "<svg/>", householdName: "Oila", fileName: "ulash.baraka" }));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    const section = screen.getByRole("region", { name: "Yangi qurilmani ulash" });
    await user.click(await within(section).findByLabelText(/^Sotuvchi/));
    await user.click(within(section).getByRole("button", { name: "Ulash faylini yaratish" }));
    expect(fns.pairingOffer).toHaveBeenCalledWith({ role: "SELLER", spaceId: "kk" });
  });

  it("K8: rolli qurilma ro'yxatda, bekor qilish — tasdiq bilan", async () => {
    fns.devices.mockResolvedValue(ok([...devices, shop]));
    fns.revokeDevice.mockResolvedValue(ok([...devices, { ...shop, revoked: true }]));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    expect(await screen.findByTestId("device-role-Do'kon telefoni")).toHaveTextContent("Sotuvchi");
    await user.click(screen.getByRole("button", { name: "Ulanishni bekor qilish" }));
    expect(fns.revokeDevice).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Ha, bekor qilish" }));
    expect(fns.revokeDevice).toHaveBeenCalledWith("dev-shop");
  });

  it("K8: sotuvchi faylidagi rad etilgan yozuvlar sababi bilan", async () => {
    fns.inspectBaraka.mockResolvedValue(
      ok(
        preview({
          conflicts: [],
          protected: [],
          ignored: 12,
          rejected: [
            { key: "kk_stock_moves:m1", table: "kk_stock_moves", rowId: "m1", label: "Shakar", reason: "INSUFFICIENT_STOCK" },
            { key: "incomes:i1", table: "incomes", rowId: "i1", label: "Shakar", reason: "LINKED_REJECTED" },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    const section = screen.getByRole("region", { name: "Import" });
    await user.click(within(section).getByRole("button", { name: "Fayl tanlash" }));
    await user.type(await within(section).findByLabelText("Fayl paroli"), "x");
    await user.click(within(section).getByRole("button", { name: "Koʻrib chiqish" }));
    const box = await within(section).findByTestId("sync-rejected");
    expect(box).toHaveTextContent("Qabul qilinmaydigan yozuvlar: 2");
    expect(box).toHaveTextContent("Tovar harakati: Shakar");
    expect(box).toHaveTextContent("Bogʻliq yozuv qabul qilinmadi");
    expect(within(section).getByText(/\(12\)/)).toBeInTheDocument();
  });

  it("K8: rolli qurilmada ulash yo'q", async () => {
    fns.deviceRole.mockResolvedValue(ok({ role: "SELLER", spaceId: "kk", spaceName: "Do'kon" }));
    wrap(<SyncScreen />);
    expect(await screen.findByText(/faqat egasining qurilmasi bilan/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Yangi qurilmani ulash" })).not.toBeInTheDocument();
  });

  it("M2: uydagi oila qurilmasi — Musofir makoniga bog'lanadi", async () => {
    fns.pairingOffer.mockResolvedValue(ok({ code: "ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ23-4567", qrSvg: "<svg/>", householdName: "Oila", fileName: "ulash.baraka" }));
    const user = userEvent.setup();
    wrap(<SyncScreen />);
    const section = screen.getByRole("region", { name: "Yangi qurilmani ulash" });
    await user.click(await within(section).findByLabelText(/^Uydagi oila qurilmasi/));
    expect(within(section).getByText(/maoshi, chet eldagi xarajatlari/)).toBeInTheDocument();
    await user.click(within(section).getByRole("button", { name: "Ulash faylini yaratish" }));
    expect(fns.pairingOffer).toHaveBeenCalledWith({ role: "HOME", spaceId: "mf" });
    expect(await screen.findByTestId("pairing-role")).toHaveTextContent("musofirning shaxsiy hisobi");
  });
});
