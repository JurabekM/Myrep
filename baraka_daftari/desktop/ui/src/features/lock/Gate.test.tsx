import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type VaultStateDto } from '../../bindings';

import { Gate } from './Gate';

vi.mock('../../bindings', () => ({
  commands: {
    vaultState: vi.fn(),
    lock: vi.fn(),
    activity: vi.fn(),
    unlock: vi.fn(),
    setupPin: vi.fn(),
  },
}));

const vaultState = vi.mocked(commands.vaultState);

function renderGate(state: VaultStateDto) {
  vaultState.mockResolvedValue({ status: 'ok', data: state });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <Gate>
        <p>maxfiy summa</p>
      </Gate>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Gate', () => {
  it('qulfda kontentni umuman render qilmaydi', async () => {
    renderGate({ kind: 'Locked', retry_after_secs: 0 });
    await screen.findByText("Daftarni ochish uchun PIN'ni kiriting.");
    expect(screen.queryByText('maxfiy summa')).not.toBeInTheDocument();
  });

  it("birinchi ishga tushirishda PIN o'rnatish ekranini ko'rsatadi", async () => {
    renderGate({ kind: 'Uninitialized' });
    expect(await screen.findByRole('button', { name: "PIN o'rnatish" })).toBeInTheDocument();
    expect(screen.queryByText('maxfiy summa')).not.toBeInTheDocument();
  });

  it("ochiq holatda kontentni ko'rsatadi", async () => {
    renderGate({ kind: 'Unlocked' });
    await waitFor(() => {
      expect(screen.getByText('maxfiy summa')).toBeInTheDocument();
    });
  });
});
