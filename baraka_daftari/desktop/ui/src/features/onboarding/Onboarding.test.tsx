import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';
import { a11yViolations } from '../../lib/axe';

import { Onboarding } from './Onboarding';

vi.mock('../../bindings', () => ({
  commands: { onboardingDone: vi.fn(), completeOnboarding: vi.fn() },
}));

function renderIt() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <Onboarding />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.completeOnboarding).mockResolvedValue({ status: 'ok', data: null });
});

describe('Onboarding', () => {
  it('bajarilgan bo‘lsa ko‘rinmaydi', async () => {
    vi.mocked(commands.onboardingDone).mockResolvedValue({ status: 'ok', data: true });
    renderIt();
    await waitFor(() => {
      expect(commands.onboardingDone).toHaveBeenCalled();
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('5 qadamdan o‘tadi va oxirida yakunlaydi', async () => {
    vi.mocked(commands.onboardingDone).mockResolvedValue({ status: 'ok', data: false });
    renderIt();
    expect(await screen.findByTestId('onb-progress')).toHaveTextContent('1-qadam / 5');
    for (let i = 2; i <= 5; i++) {
      await userEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
      expect(screen.getByTestId('onb-progress')).toHaveTextContent(`${String(i)}-qadam / 5`);
    }
    await userEvent.click(screen.getByRole('button', { name: 'Boshlash' }));
    await waitFor(() => {
      expect(commands.completeOnboarding).toHaveBeenCalledTimes(1);
    });
  });

  it('o‘tkazib yuborish ham yakunlaydi', async () => {
    vi.mocked(commands.onboardingDone).mockResolvedValue({ status: 'ok', data: false });
    renderIt();
    await userEvent.click(await screen.findByRole('button', { name: "O'tkazib yuborish" }));
    await waitFor(() => {
      expect(commands.completeOnboarding).toHaveBeenCalledTimes(1);
    });
  });

  it('accessibility: dialog axe buzilishsiz', async () => {
    vi.mocked(commands.onboardingDone).mockResolvedValue({ status: 'ok', data: false });
    renderIt();
    await screen.findByRole('dialog');
    expect(await a11yViolations(document.body)).toEqual([]);
  });
});
