import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands } from '../../bindings';

import { CraftsPage } from './CraftsPage';

vi.mock('../../bindings', () => ({
  commands: {
    listCraftIdeas: vi.fn(),
    addCraftIdea: vi.fn(),
    removeCraftIdea: vi.fn(),
    craftToContract: vi.fn(),
    checkOffer: vi.fn(),
  },
}));

const m = (formatted: string) => ({ minor: '1', currency: 'UZS', formatted });

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.listCraftIdeas).mockResolvedValue({
    status: 'ok',
    data: [
      {
        id: 'i1',
        name: 'Tikuv sexi',
        note: null,
        capex: [{ item: 'Mashina', price: m("6 000 000 so'm") }],
        capex_total: m("6 000 000 so'm"),
        share_bp: null,
        scenarios: [
          { net: m('0'), net_after_share: m('0'), payback_months: null },
          { net: m("2 000 000 so'm"), net_after_share: m("2 000 000 so'm"), payback_months: 3 },
          { net: m("3 000 000 so'm"), net_after_share: m("3 000 000 so'm"), payback_months: 2 },
        ],
      },
    ],
  });
});

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <CraftsPage />
    </QueryClientProvider>,
  );
}

describe('CraftsPage', () => {
  it('uch senariy va qaytim muddati ko‘rinadi', async () => {
    renderPage();
    expect(await screen.findByText('Tikuv sexi')).toBeInTheDocument();
    expect(screen.getByTestId('sc-Tikuv sexi-pess')).toHaveTextContent('qaytmaydi');
    expect(screen.getByTestId('sc-Tikuv sexi-avg')).toHaveTextContent('3 oy');
    expect(screen.getByTestId('sc-Tikuv sexi-opt')).toHaveTextContent('2 oy');
  });

  it('taklif detektori hukmni va belgilarni ko‘rsatadi', async () => {
    vi.mocked(commands.checkOffer).mockResolvedValue({
      verdict: 'RED',
      flags: ['GUARANTEED_PROFIT'],
    });
    renderPage();
    await screen.findByText('Tikuv sexi');
    await userEvent.click(screen.getByLabelText('Foyda kafolatlanadi'));
    await userEvent.click(screen.getByRole('button', { name: 'Tekshirish' }));
    await waitFor(() => {
      expect(screen.getByTestId('verdict')).toHaveAttribute('data-verdict', 'RED');
    });
    expect(commands.checkOffer).toHaveBeenCalledWith(
      expect.objectContaining({ guaranteed_profit: true }),
    );
    expect(screen.getByTestId('verdict')).toHaveTextContent('Foyda kafolatlanmoqda');
  });
});
