import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import i18n from "../../i18n";
import { axeViolations } from "../../test/axe";
import { HomeScreen } from "../home/HomeScreen";
import { useUi } from "../../state/ui";
import { SettingsScreen } from "./SettingsScreen";

const money = (formatted: string) => ({
  minor: "0",
  currency: "UZS",
  formatted,
  plain: "0",
});
const settings = {
  locale: "uz",
  householdLocale: "uz",
  deviceLocale: null,
  incomeRhythm: "DAILY",
  debtsDeclared: true,
};

const fns = {
  settings: vi.fn(),
  updateSettings: vi.fn(),
  homeNudges: vi.fn(),
  monthlySummary: vi.fn(),
  vault: vi.fn(),
  debtsOverview: vi.fn(),
  agreementReminders: vi.fn(),
};
vi.mock("../../bindings", () => ({
  commands: new Proxy(
    {},
    {
      get:
        (_t, name: string) =>
        (...a: unknown[]) =>
          (fns as Record<string, (...x: unknown[]) => unknown>)[name]?.(...a) ??
          new Promise(() => {}),
    },
  ),
}));

const ok = (data: unknown) => ({ status: "ok", data });

function wrap(ui: ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );
}

beforeEach(async () => {
  Object.values(fns).forEach((f) => f.mockReset());
  fns.settings.mockResolvedValue(ok(settings));
  fns.updateSettings.mockImplementation((input: { locale: string | null }) =>
    Promise.resolve(
      ok({
        ...settings,
        ...input,
        deviceLocale: input.locale,
        locale: input.locale ?? "uz",
      }),
    ),
  );
  fns.monthlySummary.mockResolvedValue(
    ok({ paidToSelf: money("0 soʻm"), monthResult: money("0 soʻm") }),
  );
  fns.vault.mockResolvedValue(
    ok({ balance: money("0 soʻm"), streak: { currentWeeks: 0 } }),
  );
  fns.debtsOverview.mockResolvedValue(ok({ debtFreeDate: null }));
  fns.agreementReminders.mockResolvedValue(ok([]));
  window.localStorage.clear();
  document.documentElement.style.fontSize = "";
  await i18n.changeLanguage("uz");
});

describe("Sozlamalar", () => {
  it("til shu qurilmaga yoziladi va UI almashadi; shrift kattalashadi", async () => {
    const user = userEvent.setup();
    const { container } = wrap(<SettingsScreen />);
    const lang = await screen.findByRole("radiogroup", {
      name: "Til (shu qurilma)",
    });
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(lang).getByLabelText("Русский"));
    expect(fns.updateSettings).toHaveBeenCalledWith({
      locale: "ru",
      incomeRhythm: "DAILY",
      debtsDeclared: true,
    });
    expect(
      await screen.findByRole("heading", { name: "Настройки" }),
    ).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("ru");

    await user.click(screen.getByLabelText("130%"));
    expect(document.documentElement.style.fontSize).toBe("130%");
    expect(
      JSON.parse(window.localStorage.getItem("baraka.display") ?? "{}"),
    ).toMatchObject({ fontScale: 130, locale: "ru" });
  });

  it("daromad ritmi va qarz eslatmasi xonadon uchun saqlanadi", async () => {
    const user = userEvent.setup();
    wrap(<SettingsScreen />);
    await user.click(await screen.findByLabelText(/Buyurtma boʻyicha/));
    expect(fns.updateSettings).toHaveBeenLastCalledWith({
      locale: null,
      incomeRhythm: "ORDERS",
      debtsDeclared: true,
    });
    await user.click(screen.getByLabelText(/Qarzlarim bor/));
    expect(fns.updateSettings).toHaveBeenLastCalledWith({
      locale: null,
      incomeRhythm: "DAILY",
      debtsDeclared: false,
    });
  });
});

describe("Bosh sahifa eslatmalari", () => {
  it("har biri o'z ekraniga olib boradi; qarz eslatmasini o'chirsa bo'ladi", async () => {
    fns.homeNudges.mockResolvedValue(
      ok([
        { kind: "INCOME_TODAY", days: null },
        { kind: "DEBT_INVENTORY", days: null },
        { kind: "BACKUP", days: 31 },
      ]),
    );
    useUi.setState({ screen: "home", incomeOpen: false });
    const user = userEvent.setup();
    const { container } = wrap(<HomeScreen spaceId="uy" />);
    const backup = await screen.findByTestId("nudge-BACKUP");
    expect(backup).toHaveTextContent("Zaxira nusxa olinmaganiga 31 kun boʻldi");
    expect(await axeViolations(container)).toEqual([]);

    await user.click(
      within(screen.getByTestId("nudge-INCOME_TODAY")).getByRole("button", {
        name: "Daromad kiritish",
      }),
    );
    expect(useUi.getState().incomeOpen).toBe(true);
    await user.click(
      within(backup).getByRole("button", { name: "Zaxira olish" }),
    );
    expect(useUi.getState().screen).toBe("sync");
    const debts = screen.getByTestId("nudge-DEBT_INVENTORY");
    await user.click(within(debts).getByRole("button", { name: "Eslatmasin" }));
    expect(fns.updateSettings).toHaveBeenCalledWith({
      locale: null,
      incomeRhythm: "DAILY",
      debtsDeclared: false,
    });
    await user.click(
      within(debts).getByRole("button", { name: "Qarzlarni yozish" }),
    );
    expect(useUi.getState().screen).toBe("inventory");
  });
});
