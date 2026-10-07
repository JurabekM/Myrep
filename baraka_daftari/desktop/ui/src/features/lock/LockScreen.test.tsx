import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';

import { LockScreen } from './LockScreen';

vi.mock('../../bindings', () => ({
  commands: { unlock: vi.fn(), setupPin: vi.fn() },
}));

const unlock = vi.mocked(commands.unlock);
const setupPin = vi.mocked(commands.setupPin);

function renderScreen(props: { setup: boolean; retryAfterSecs: number }) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <LockScreen {...props} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('LockScreen', () => {
  it("6 raqamdan kam bo'lsa tugma o'chiq, PIN faqat raqamlarni qabul qiladi", async () => {
    renderScreen({ setup: false, retryAfterSecs: 0 });
    const button = screen.getByRole('button', { name: 'Ochish' });
    const input = screen.getByLabelText('PIN (6 raqam)');
    await userEvent.type(input, '12ab345');
    expect(input).toHaveValue('12345');
    expect(button).toBeDisabled();
    await userEvent.type(input, '6');
    expect(button).toBeEnabled();
  });

  it("PIN'ni Rustga yuboradi va xatoda tozalab, xabar ko'rsatadi", async () => {
    unlock.mockResolvedValue({ status: 'error', error: { kind: 'WrongPin' } });
    renderScreen({ setup: false, retryAfterSecs: 0 });
    const input = screen.getByLabelText('PIN (6 raqam)');
    await userEvent.type(input, '123456');
    await userEvent.click(screen.getByRole('button', { name: 'Ochish' }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent("PIN noto'g'ri.");
    });
    expect(unlock).toHaveBeenCalledWith('123456');
    expect(input).toHaveValue('');
  });

  it("o'rnatishda PIN'lar mos kelmasa Rustga yubormaydi", async () => {
    renderScreen({ setup: true, retryAfterSecs: 0 });
    await userEvent.type(screen.getByLabelText('Yangi PIN (6 raqam)'), '123456');
    await userEvent.type(screen.getByLabelText("PIN'ni takrorlang"), '654321');
    await userEvent.click(screen.getByRole('button', { name: "PIN o'rnatish" }));
    expect(screen.getByRole('alert')).toHaveTextContent("PIN'lar bir xil emas.");
    expect(setupPin).not.toHaveBeenCalled();
  });

  it("o'rnatish mos PIN'lar bilan setupPin chaqiradi", async () => {
    setupPin.mockResolvedValue({ status: 'ok', data: null });
    renderScreen({ setup: true, retryAfterSecs: 0 });
    await userEvent.type(screen.getByLabelText('Yangi PIN (6 raqam)'), '123456');
    await userEvent.type(screen.getByLabelText("PIN'ni takrorlang"), '123456');
    await userEvent.click(screen.getByRole('button', { name: "PIN o'rnatish" }));
    await waitFor(() => {
      expect(setupPin).toHaveBeenCalledWith('123456');
    });
  });

  it("kutish vaqtida kiritish bloklanadi va soniyalar ko'rsatiladi", async () => {
    renderScreen({ setup: false, retryAfterSecs: 30 });
    await userEvent.type(screen.getByLabelText('PIN (6 raqam)'), '123456');
    expect(screen.getByRole('button', { name: 'Ochish' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent('30 soniyadan keyin');
  });
});
