import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { useNav } from '../../app/nav';
import { commands, type ChapterDetailDto, type JourneyDto } from '../../bindings';

import { StudyPage } from './StudyPage';

vi.mock('../../bindings', () => ({
  commands: {
    journey: vi.fn(),
    chapterDetail: vi.fn(),
    setTaskDone: vi.fn(),
    savePage: vi.fn(),
    setUnlockPolicy: vi.fn(),
  },
}));

const journey: JourneyDto = {
  chapters: [
    {
      id: 'ch01',
      title: "Avval o'zingga to'la",
      law: 1,
      order: 1,
      opened: true,
      opened_on: '2026-10-02',
      is_current: true,
    },
    {
      id: 'ch02',
      title: 'Xurjunning teshigini yama',
      law: 2,
      order: 2,
      opened: false,
      opened_on: null,
      is_current: false,
    },
  ],
  current_id: 'ch01',
  current_title: "Avval o'zingga to'la",
  opened_this_week: false,
  week_start: '2026-10-09',
  week_tasks: [],
  week_done: 0,
  unlock: { unlocked: false, satisfied_weeks: 1, needed_weeks: 2, weeks_in_window: 1 },
  policy: { window_weeks: 3, min_satisfied_weeks: 2, min_tasks_per_week: 2 },
};

const detail: ChapterDetailDto = {
  id: 'ch01',
  title: "Avval o'zingga to'la",
  law: 1,
  placeholder: true,
  blocks: [
    { id: 'b1', text: '[Placeholder] matn', source: null, unreviewed: false },
    { id: 'b3', text: '[Diniy matn o‘rni]', source: 'Manba kutilmoqda', unreviewed: true },
  ],
  page_prompt: "Qonunni o'z so'zingiz bilan yozing.",
  page_body: 'Mening yozuvim',
  tasks: [
    { id: 'ch01-t1', title: 'Daromad kiriting', done: true, auto_detected: true, manual: false },
    { id: 'ch01-t4', title: "Qo'lda vazifa", done: false, auto_detected: false, manual: true },
  ],
};

function renderStudy() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <StudyPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useNav.setState({ page: 'study', chapterId: null });
  vi.mocked(commands.journey).mockResolvedValue({ status: 'ok', data: journey });
  vi.mocked(commands.chapterDetail).mockResolvedValue({ status: 'ok', data: detail });
  vi.mocked(commands.setTaskDone).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.savePage).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.setUnlockPolicy).mockResolvedValue({ status: 'ok', data: null });
});

describe('StudyPage', () => {
  it("ochiq bobni ko'rsatadi, qulflangan bob tugmasi o'chiq va ochilish holati yoziladi", async () => {
    renderStudy();
    expect(
      await screen.findByRole('heading', { name: "Avval o'zingga to'la", level: 2 }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xurjunning teshigini yama/ })).toBeDisabled();
    expect(screen.getByTestId('unlock-info')).toHaveTextContent('1 / 2 hafta');
    // Ta'limiy ekranda disklеymer.
    expect(screen.getAllByText(/Fatvo yoki moliyaviy maslahat emas/).length).toBeGreaterThan(0);
  });

  it("tasdiqlanmagan diniy blok manba va belgi bilan ko'rsatiladi (faqat server yuborsa)", async () => {
    renderStudy();
    expect(await screen.findByText('Manba kutilmoqda')).toBeInTheDocument();
    expect(screen.getByText('Tekshirilmagan')).toBeInTheDocument();
  });

  it("qo'lda vazifa belgilanadi, avtomatik vazifa o'chiq", async () => {
    renderStudy();
    const auto = await screen.findByRole('checkbox', { name: /Daromad kiriting/ });
    expect(auto).toBeChecked();
    expect(auto).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox', { name: /Qo'lda vazifa/ }));
    expect(commands.setTaskDone).toHaveBeenCalledWith('ch01', 'ch01-t4', true);
  });

  it('Daftar sahifasi faqat o‘zgargandan keyin saqlanadi', async () => {
    renderStudy();
    const region = await screen.findByRole('region', { name: 'Daftar sahifasi' });
    const box = within(region).getByRole('textbox');
    expect(box).toHaveValue('Mening yozuvim');
    const save = within(region).getByRole('button', { name: 'Saqlash' });
    expect(save).toBeDisabled();
    await userEvent.type(box, ' +');
    await userEvent.click(save);
    await waitFor(() => {
      expect(commands.savePage).toHaveBeenCalledWith('ch01', 'Mening yozuvim +');
    });
  });

  it('ochilish sharti sozlamasi Rustga raqamlar bilan yuboriladi', async () => {
    renderStudy();
    const summary = await screen.findByText('Ochilish shartini sozlash');
    await userEvent.click(summary);
    const details = within(summary.closest('details') as HTMLElement);
    const window = details.getByLabelText('Oxirgi N hafta');
    await userEvent.clear(window);
    await userEvent.type(window, '4');
    await userEvent.click(details.getByRole('button', { name: 'Saqlash' }));
    await waitFor(() => {
      expect(commands.setUnlockPolicy).toHaveBeenCalledWith({
        window_weeks: 4,
        min_satisfied_weeks: 2,
        min_tasks_per_week: 2,
      });
    });
  });

  it('bosh sahifadan tanlangan bob ochiladi', async () => {
    useNav.setState({ chapterId: 'ch01' });
    renderStudy();
    await screen.findByRole('heading', { level: 2 });
    expect(commands.chapterDetail).toHaveBeenCalledWith('ch01');
  });
});
