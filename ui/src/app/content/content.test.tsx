import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type ChapterCardDto,
  type ChapterDto,
  type WeeklyTasksDto,
  commands,
} from "../../bindings/bindings";
import { setAppLanguage } from "../../i18n";
import { resetFinanceMocks } from "../../test/fixtures";
import { App } from "../App";
import { useUiStore } from "../store";

// Kontent oqimlari: IPC soxtalashtiriladi, ko'rinish va o'zaro ta'sir haqiqiy komponentlarda sinaladi.
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
    getChapter: vi.fn(),
    getWeeklyTasks: vi.fn(),
    setTaskDone: vi.fn(),
    saveDaftarPage: vi.fn(),
  },
}));

const APP_INFO = {
  name: "Baraka Dastur",
  version: "0.1.0",
  platform: "windows",
  arch: "x86_64",
  buildProfile: "release",
};

const FIRST: ChapterCardDto = {
  id: "ch01",
  order: 1,
  title: { uz: "Nimaga qoladi?", ru: "Что остаётся?" },
  unlocked: true,
  unlockDate: null,
  tasksRemaining: 0,
  notBefore: null,
};

const SECOND: ChapterCardDto = {
  id: "ch02",
  order: 2,
  title: { uz: "Xurjunning teshigi", ru: "Дыра в хурджуне" },
  unlocked: false,
  unlockDate: null,
  tasksRemaining: 2,
  notBefore: "2026-10-21",
};

const TASKS = [
  {
    id: "ch01.t1",
    text: { uz: "Kelajagim jamgʻarmangizni oching.", ru: "Откройте «Будущее»." },
    autoCompleted: true,
    done: false,
  },
  {
    id: "ch01.t2",
    text: { uz: "Shu hafta ulush ajrating.", ru: "Отложите долю на этой неделе." },
    autoCompleted: false,
    done: false,
  },
  {
    id: "ch01.t3",
    text: { uz: "Auditni oʻtkazing.", ru: "Проведите аудит." },
    autoCompleted: true,
    done: false,
  },
];

function chapterView(overrides: Partial<ChapterDto> = {}): ChapterDto {
  return {
    id: "ch01",
    order: 1,
    title: { uz: "Nimaga qoladi?", ru: "Что остаётся?" },
    blocks: [
      { type: "paragraph", text: { uz: "Qissa matni.", ru: "Текст истории." } },
      {
        type: "religious",
        text: { uz: "Oyat matni.", ru: "Текст аята." },
        source: { uz: "Baqara 2:286", ru: "Бакара 2:286" },
        approved: false,
      },
    ],
    law: { number: 1, text: { uz: "Qonun matni.", ru: "Текст закона." } },
    weeklyTasks: TASKS,
    isCurrent: true,
    audioUrl: null,
    daftarPage: null,
    ...overrides,
  };
}

const WEEK: WeeklyTasksDto = {
  chapterId: "ch01",
  chapterTitle: { uz: "Nimaga qoladi?", ru: "Что остаётся?" },
  weekStart: "2026-10-09",
  tasks: TASKS,
};

function setUp(): void {
  vi.mocked(commands.getAppInfo).mockResolvedValue(APP_INFO);
  vi.mocked(commands.getSecurityStatus).mockResolvedValue({
    status: "ok",
    data: { setUp: true, unlocked: true },
  });
  resetFinanceMocks();
  vi.mocked(commands.listChapters).mockResolvedValue({ status: "ok", data: [FIRST, SECOND] });
  vi.mocked(commands.getChapter).mockResolvedValue({ status: "ok", data: chapterView() });
  vi.mocked(commands.getWeeklyTasks).mockResolvedValue({ status: "ok", data: WEEK });
  vi.mocked(commands.setTaskDone).mockResolvedValue({ status: "ok", data: WEEK });
  vi.mocked(commands.saveDaftarPage).mockResolvedValue({
    status: "ok",
    data: { chapterId: "ch01", lawNumber: 1, body: "Matn", updatedOn: "2026-10-14" },
  });
}

/** Boblar ro'yxatidan birinchi bobni ochadi va kutilgan sarlavha chiqqanini kutadi. */
async function openChapter(
  user: ReturnType<typeof userEvent.setup>,
  heading = "Nimaga qoladi?",
): Promise<void> {
  useUiStore.setState({ page: "chapters" });
  render(<App />);
  await user.click(await screen.findByRole("button", { name: /Nimaga qoladi/ }));
  await screen.findByRole("heading", { level: 1, name: heading });
}

describe("bob kontenti", () => {
  beforeEach(() => {
    setUp();
    useUiStore.setState({ page: "home", quickEntryOpen: false });
  });

  afterEach(async () => {
    vi.clearAllMocks();
    await setAppLanguage("uz");
  });

  it("ro'yxat: ochiq bob bosiladi, yopiq bob ochilish shartini koʻrsatadi", async () => {
    useUiStore.setState({ page: "chapters" });
    render(<App />);

    await screen.findByRole("heading", { level: 1, name: "Boblar" });
    expect(await screen.findByRole("button", { name: /Nimaga qoladi/ })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Xurjunning teshigi/ })).not.toBeInTheDocument();
    expect(screen.getByText("Yana 2 ta vazifani bajaring")).toBeInTheDocument();
    expect(screen.getByText("Eng erta sana: 21.10.2026")).toBeInTheDocument();
  });

  it("bob sahifasi: qonun va vazifalar, tasdiqlanmagan diniy blok belgi bilan", async () => {
    const user = userEvent.setup();
    await openChapter(user);

    expect(screen.getByText("Qonun matni.")).toBeInTheDocument();
    expect(screen.getByText("Qissa matni.")).toBeInTheDocument();
    expect(screen.getByText("Oyat matni.")).toBeInTheDocument();
    expect(screen.getByText(/Ulamo tekshiruvida/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Kelajagim jamgʻarmangizni/ })).toBeEnabled();
  });

  it("joriy bobda vazifa belgilanadi va backend'ga yuboriladi", async () => {
    const user = userEvent.setup();
    await openChapter(user);

    await user.click(screen.getByRole("checkbox", { name: /Shu hafta ulush ajrating/ }));

    expect(commands.setTaskDone).toHaveBeenCalledWith("ch01.t2", true);
  });

  it("joriy bo'lmagan bobda vazifalar faqat ko'rsatiladi", async () => {
    vi.mocked(commands.getChapter).mockResolvedValue({
      status: "ok",
      data: chapterView({ isCurrent: false }),
    });
    const user = userEvent.setup();
    await openChapter(user);

    expect(screen.getByRole("checkbox", { name: /Shu hafta ulush ajrating/ })).toBeDisabled();
    expect(screen.getByText(/Bu bob joriy emas/)).toBeInTheDocument();
  });

  it("«Daftar sahifasi»: boʻsh matn saqlanmaydi, matn yuboriladi", async () => {
    const user = userEvent.setup();
    await openChapter(user);

    const save = screen.getByRole("button", { name: "Sahifani saqlash" });
    expect(save).toBeDisabled();

    await user.type(screen.getByLabelText("«Daftar sahifasi»"), "  Qarzni yopish rejasi  ");
    await user.click(save);

    expect(commands.saveDaftarPage).toHaveBeenCalledWith("ch01", "  Qarzni yopish rejasi  ");
  });

  it("«Daftar sahifasi»: backend xatosi o'zbekcha matnga aylanadi", async () => {
    vi.mocked(commands.saveDaftarPage).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "BODY_TOO_LONG" },
    });
    const user = userEvent.setup();
    await openChapter(user);

    await user.type(screen.getByLabelText("«Daftar sahifasi»"), "Matn");
    await user.click(screen.getByRole("button", { name: "Sahifani saqlash" }));

    expect(
      await screen.findByText("Sahifa matni 5000 belgidan oshmasligi kerak."),
    ).toBeInTheDocument();
  });

  it("yopiq bob (CHAPTER_LOCKED): ochilish shartini tushuntiradi", async () => {
    vi.mocked(commands.getChapter).mockResolvedValue({
      status: "error",
      error: { code: "RULE", rule: "CHAPTER_LOCKED" },
    });
    const user = userEvent.setup();
    await openChapter(user, "Bu bob hali ochilmagan");

    expect(
      screen.getByText("Oldingi bobning vazifalarini bajaring va kun shartini kuting."),
    ).toBeInTheDocument();
  });

  it("bosh sahifa: haftalik vazifa belgilanadi", async () => {
    const user = userEvent.setup();
    render(<App />);

    const heading = await screen.findByRole("heading", {
      level: 2,
      name: "Shu haftaning vazifalari",
    });
    const card = heading.parentElement;
    if (card === null) {
      throw new Error("Kartochka topilmadi");
    }
    await user.click(
      await within(card).findByRole("checkbox", { name: /Shu hafta ulush ajrating/ }),
    );

    expect(commands.setTaskDone).toHaveBeenCalledWith("ch01.t2", true);
  });

  it("bosh sahifa: ochiq bob bo'lmasa, shuni koʻrsatadi", async () => {
    vi.mocked(commands.getWeeklyTasks).mockResolvedValue({ status: "ok", data: null });
    render(<App />);

    expect(await screen.findByText("Hozircha ochiq bob yoʻq.")).toBeInTheDocument();
    await waitFor(() => {
      expect(commands.getWeeklyTasks).toHaveBeenCalled();
    });
  });
});
