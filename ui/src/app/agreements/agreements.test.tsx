import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type AgreementDto, type AgreementSummaryDto, commands } from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { money, resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Kelishuv ustasi: IPC soxta; 9/9 bo'lmaguncha imzolash yopiq, saqlash javoblarni yuboradi, imzo chizish.
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
    listAgreements: vi.fn(),
    getAgreementsCenter: vi.fn(),
    listFamilyTemplates: vi.fn(),
    getAgreementOps: vi.fn(),
    createAgreement: vi.fn(),
    getAgreement: vi.fn(),
    saveAgreementAnswers: vi.fn(),
    addSignature: vi.fn(),
    signAgreement: vi.fn(),
    getJournal: vi.fn(),
    appendJournalEntry: vi.fn(),
    createAgreementPdf: vi.fn(),
  },
}));

const ID = "0192e000-0000-7000-8000-0000000000a9";

const EMPTY_ANSWERS: AgreementDto["answers"] = {
  parties: [],
  contributions: [],
  duties: [],
  hasSchedule: false,
  profitShares: [],
  profitFixedAmount: "",
  profitNotApplicable: null,
  lossText: "",
  lossNotApplicable: null,
  custodyLocation: "",
  keeperPartyId: null,
  reviewEveryDays: 30,
  exitNoticeDays: 30,
  exitValuation: "",
  exitPayout: "",
  exitAssets: "",
  exitNotApplicable: null,
  arbiterName: "",
  arbiterRole: "",
  termMonths: 12,
  reviewDate: "",
};

const DRAFT: AgreementDto = {
  id: ID,
  kind: "PARTNERSHIP",
  title: "Non sexi",
  status: "DRAFT",
  version: 1,
  effectiveFrom: null,
  answers: EMPTY_ANSWERS,
  completeness: { complete: false, missing: [1, 2, 3, 4, 5, 6, 7, 8, 9], errors: [] },
  signatures: [],
  journalCount: 0,
  chainHead: null,
  chainOk: true,
  canWriteJournal: false,
};

const SUMMARY: AgreementSummaryDto = {
  id: ID,
  kind: "PARTNERSHIP",
  title: "Non sexi",
  status: "DRAFT",
  version: 1,
  answered: 0,
  reviewDate: null,
};

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
  vi.mocked(commands.listAgreements).mockResolvedValue({ status: "ok", data: [SUMMARY] });
  vi.mocked(commands.getAgreementsCenter).mockResolvedValue({
    status: "ok",
    data: {
      rows: [
        {
          id: ID,
          kind: "PARTNERSHIP",
          title: "Non sexi",
          status: "DRAFT",
          version: 1,
          reviewDate: null,
          reviewDue: false,
          openIncidents: 0,
          openDisputes: 0,
          chainOk: true,
          familyPending: 0,
        },
      ],
    },
  });
  vi.mocked(commands.listFamilyTemplates).mockResolvedValue({ status: "ok", data: [] });
  vi.mocked(commands.getAgreement).mockResolvedValue({ status: "ok", data: DRAFT });
  vi.mocked(commands.getJournal).mockResolvedValue({
    status: "ok",
    data: { entries: [], chainOk: true, firstBroken: null },
  });
}

async function openWizard(): Promise<HTMLElement> {
  useUiStore.setState({ page: "partnerships" });
  render(<App />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Ochish" }));
  return screen.findByRole("dialog", { name: "Non sexi" });
}

describe("kelishuv ustasi", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("ro'yxat va qoralama yaratish", async () => {
    vi.mocked(commands.createAgreement).mockResolvedValue({
      status: "ok",
      data: { ...DRAFT, id: "0192e000-0000-7000-8000-0000000000b9", title: "Oila" },
    });
    useUiStore.setState({ page: "partnerships" });
    render(<App />);
    expect(await screen.findByText("Non sexi")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Kelishuvlar markazi" })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Turi"), "FAMILY");
    await user.type(screen.getByLabelText(/Sarlavha/), "Oila");
    await user.click(screen.getByRole("button", { name: "Qoralama yaratish" }));
    expect(commands.createAgreement).toHaveBeenCalledWith({ kind: "FAMILY", title: "Oila" });
  });

  it("9/9 bo'lmaguncha imzolash yopiq; tomon qo'shib saqlash javoblarni yuboradi", async () => {
    vi.mocked(commands.saveAgreementAnswers).mockResolvedValue({
      status: "ok",
      data: {
        ...DRAFT,
        version: 2,
        completeness: { complete: false, missing: [2, 3, 4, 5, 6, 7, 8, 9], errors: [] },
      },
    });
    const dialog = await openWizard();
    expect(within(dialog).getByRole("button", { name: "Imzolash" })).toBeDisabled();
    expect(within(dialog).getByText("0 / 9 savolga javob berildi")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(within(dialog).getByRole("button", { name: "Tomon qo'shish" }));
    await user.click(within(dialog).getByRole("button", { name: "Tomon qo'shish" }));
    const [firstName, secondName] = within(dialog).getAllByLabelText("Ism-sharif");
    if (firstName === undefined || secondName === undefined) {
      throw new Error("ikki tomon maydoni kutilgan");
    }
    await user.type(firstName, "Anvar Karimov");
    await user.type(secondName, "Dilshod Rahimov");
    await user.click(within(dialog).getByRole("button", { name: "Saqlash" }));

    expect(await within(dialog).findByText("1 / 9 savolga javob berildi")).toBeInTheDocument();
    const call = vi.mocked(commands.saveAgreementAnswers).mock.calls[0]?.[0];
    expect(call?.version).toBe(1);
    expect(call?.answers.parties.map((p) => p.name)).toEqual(["Anvar Karimov", "Dilshod Rahimov"]);
    expect(call?.answers.parties[0]?.isMe).toBe(true);
  });

  it("to'liq kelishuvda imzo chiziladi va yuboriladi", async () => {
    const complete: AgreementDto = {
      ...DRAFT,
      answers: {
        ...EMPTY_ANSWERS,
        parties: [
          { id: "P1", name: "Anvar Karimov", role: "sherik", relation: "", isMe: true },
          { id: "P2", name: "Dilshod Rahimov", role: "sherik", relation: "", isMe: false },
        ],
      },
      completeness: { complete: true, missing: [], errors: [] },
    };
    vi.mocked(commands.getAgreement).mockResolvedValue({ status: "ok", data: complete });
    vi.mocked(commands.addSignature).mockResolvedValue({
      status: "ok",
      data: {
        ...complete,
        signatures: [
          {
            partyId: "P1",
            role: "PARTY",
            version: 1,
            signedAt: "2026-10-15T06:00:00Z",
            image: "data:image/png;base64,x",
          },
        ],
      },
    });
    // jsdom'da canvas yo'q: chizish va PNG eksporti soxtalashtiriladi.
    const context = {
      lineWidth: 0,
      lineCap: "butt",
      strokeStyle: "",
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
      clearRect: vi.fn(),
    };
    HTMLCanvasElement.prototype.getContext = vi.fn(
      () => context,
    ) as unknown as HTMLCanvasElement["getContext"];
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,QUJD");
    HTMLCanvasElement.prototype.setPointerCapture = vi.fn();

    const dialog = await openWizard();
    const user = userEvent.setup();
    await user.click(within(dialog).getByRole("button", { name: "Imzolash" }));
    const pad = within(dialog).getByRole("img", { name: "Anvar Karimov (tomon)" });
    await user.pointer([
      { keys: "[MouseLeft>]", target: pad, coords: { x: 10, y: 10 } },
      { target: pad, coords: { x: 40, y: 30 } },
      { keys: "[/MouseLeft]", target: pad },
    ]);
    const [saveButton] = within(dialog).getAllByRole("button", { name: "Imzoni saqlash" });
    if (saveButton === undefined) {
      throw new Error("imzo saqlash tugmasi kutilgan");
    }
    await user.click(saveButton);
    expect(commands.addSignature).toHaveBeenCalledWith({
      agreementId: ID,
      partyId: "P1",
      role: "PARTY",
      image: "data:image/png;base64,QUJD",
    });
    expect(
      await within(dialog).findByText(/Anvar Karimov \(tomon\) — imzolangan/),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Imzolashni yakunlash" })).toBeDisabled();
    expect(money(0, "0").minor).toBe("0");
  });
});
