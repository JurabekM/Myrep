import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import { useUi } from "../../state/ui";
import { axeViolations } from "../../test/axe";
import { SetupScreen } from "./SetupScreen";

const fns = {
  setup: vi.fn(),
  joinHousehold: vi.fn(),
  pickBarakaFile: vi.fn(),
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

beforeEach(() => {
  Object.values(fns).forEach((f) => f.mockReset());
  fns.setup.mockResolvedValue(
    ok({ household: { id: "h1" }, recoveryCode: "AAAA-BBBB-CCCC" }),
  );
  fns.pickBarakaFile.mockResolvedValue(
    ok({ path: "/tmp/x.baraka", name: "x.baraka" }),
  );
  useUi.setState({ screen: "home" });
});

describe("Onboarding (≤ 5 qadam)", () => {
  it("til → oila → daromad → qarz → PIN; qarz bo'lsa — qarzlar ekrani", async () => {
    const user = userEvent.setup();
    const { container } = wrap(<SetupScreen />);
    expect(screen.getByTestId("setup-progress")).toHaveTextContent(
      "Qadam 1 / 5",
    );
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Davom etish" }));

    // 2. Oila: nom va ism bo'lmaguncha davom etilmaydi.
    expect(screen.getByTestId("setup-progress")).toHaveTextContent(
      "Qadam 2 / 5",
    );
    const next = screen.getByRole("button", { name: "Davom etish" });
    expect(next).toBeDisabled();
    await user.type(screen.getByLabelText("Oila nomi"), "Bekzodlar oilasi");
    await user.type(screen.getByLabelText("Ismingiz"), "Bekzod");
    await user.click(screen.getByRole("button", { name: "+ Aʼzo qoʻshish" }));
    await user.type(screen.getByLabelText("2-aʼzo ismi"), "Mohira");
    await user.click(screen.getByRole("button", { name: "+ Aʼzo qoʻshish" }));
    await user.type(screen.getByLabelText("3-aʼzo ismi"), "Jasur");
    await user.selectOptions(
      screen.getByLabelText("3-aʼzo: katta yoki bola"),
      "CHILD",
    );
    expect(await axeViolations(container)).toEqual([]);
    await user.click(next);

    // 3. Daromad ritmi; oylik maoshda — maosh kuni.
    expect(screen.getByRole("button", { name: "Davom etish" })).toBeDisabled();
    await user.click(screen.getByLabelText(/Oylik maosh/));
    await user.selectOptions(
      screen.getByLabelText(/Maosh qaysi kuni keladi/),
      "10",
    );
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Davom etish" }));

    // 4. Qarz bormi.
    await user.click(screen.getByLabelText(/Ha, bor/));
    await user.click(screen.getByRole("button", { name: "Davom etish" }));

    // 5. PIN: mos kelmasa — xato.
    expect(screen.getByTestId("setup-progress")).toHaveTextContent(
      "Qadam 5 / 5",
    );
    await user.type(screen.getByLabelText("6 xonali PIN"), "246810");
    await user.type(screen.getByLabelText("PINʼni takrorlang"), "246811");
    await user.click(screen.getByRole("button", { name: "Boshlash" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "PINʼlar mos kelmadi",
    );
    expect(fns.setup).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText("PINʼni takrorlang"));
    await user.type(screen.getByLabelText("PINʼni takrorlang"), "246810");
    await user.click(screen.getByRole("button", { name: "Boshlash" }));

    expect(fns.setup).toHaveBeenCalledWith("246810", {
      householdName: "Bekzodlar oilasi",
      deviceName: "Desktop",
      platform: "desktop",
      locale: "uz",
      baseCurrency: "UZS",
      monthStartDay: 10,
      spaces: ["UY"],
      members: [
        { displayName: "Bekzod", role: "ADULT" },
        { displayName: "Mohira", role: "ADULT" },
        { displayName: "Jasur", role: "CHILD" },
      ],
      incomeRhythm: "MONTHLY",
      debtsDeclared: true,
    });
    expect(await screen.findByTestId("recovery-code")).toHaveTextContent(
      "AAAA-BBBB-CCCC",
    );
    expect(screen.getByText(/zaxira nusxa yordam beradi/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yozib oldim" }));
    expect(useUi.getState().screen).toBe("inventory");
  });

  it("orqaga qaytganda javoblar saqlanadi; qarzsizda bosh sahifa", async () => {
    const user = userEvent.setup();
    wrap(<SetupScreen />);
    await user.click(screen.getByRole("button", { name: "Davom etish" }));
    await user.type(screen.getByLabelText("Oila nomi"), "Oila");
    await user.type(screen.getByLabelText("Ismingiz"), "Feruza");
    await user.click(screen.getByRole("button", { name: "Davom etish" }));
    await user.click(screen.getByLabelText(/Har kuni naqd/));
    await user.click(screen.getByRole("button", { name: "Orqaga" }));
    expect(screen.getByLabelText("Oila nomi")).toHaveValue("Oila");
    await user.click(screen.getByRole("button", { name: "Davom etish" }));
    expect(screen.getByLabelText(/Har kuni naqd/)).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Davom etish" }));
    await user.click(screen.getByLabelText(/^Yoʻq/));
    await user.click(screen.getByRole("button", { name: "Davom etish" }));
    await user.type(screen.getByLabelText("6 xonali PIN"), "135790");
    await user.type(screen.getByLabelText("PINʼni takrorlang"), "135790");
    await user.click(screen.getByRole("button", { name: "Boshlash" }));
    expect(fns.setup.mock.calls[0]?.[1]).toMatchObject({
      incomeRhythm: "DAILY",
      debtsDeclared: false,
      monthStartDay: 1,
    });
    await user.click(
      await screen.findByRole("button", { name: "Yozib oldim" }),
    );
    expect(useUi.getState().screen).toBe("home");
  });

  it("mavjud xonadonga qo'shilish: fayl, kod va PIN", async () => {
    fns.joinHousehold.mockResolvedValue(
      ok({ household: { id: "h1" }, recoveryCode: "AAAA-BBBB" }),
    );
    const user = userEvent.setup();
    const { container } = wrap(<SetupScreen />);
    await user.click(screen.getByLabelText(/Mavjud xonadonga qoʻshilish/));
    expect(screen.queryByLabelText("Oila nomi")).not.toBeInTheDocument();
    const submit = screen.getByRole("button", { name: "Qoʻshilish" });
    expect(submit).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Fayl tanlash" }));
    expect(await screen.findByText("x.baraka")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Ulash kodi yoki zaxira nusxa paroli"),
      "abcd efgh",
    );
    await user.type(screen.getByLabelText("6 xonali PIN"), "445566");
    await user.type(screen.getByLabelText("PINʼni takrorlang"), "445566");
    expect(await axeViolations(container)).toEqual([]);
    await user.click(submit);
    expect(fns.joinHousehold).toHaveBeenCalledWith("/tmp/x.baraka", "445566", {
      secret: "abcd efgh",
      deviceName: "Desktop",
      platform: "desktop",
    });
    expect(await screen.findByTestId("recovery-code")).toHaveTextContent(
      "AAAA-BBBB",
    );
  });
});
