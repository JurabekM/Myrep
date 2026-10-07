import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import '../../i18n';
import { commands, type PriceBookDto, type PriceItemDto } from '../../bindings';

import { PricesPage } from './PricesPage';

vi.mock('../../bindings', () => ({
  commands: {
    listPriceItems: vi.fn(),
    priceBook: vi.fn(),
    addPriceItem: vi.fn(),
    addPrice: vi.fn(),
    priceHistory: vi.fn(),
    removePriceItem: vi.fn(),
    purchasingPower: vi.fn(),
  },
}));

const money = (formatted: string) => ({ minor: '0', currency: 'UZS', formatted });

const meat: PriceItemDto = {
  id: 'm1',
  name: "Go'sht",
  unit: 'kg',
  weight_bp: 5000,
  active: true,
  first: { id: 'p1', price: money("80 000 so'm"), observed_on: '2023-10-07', place: null },
  last: { id: 'p2', price: money("130 000 so'm"), observed_on: '2026-10-07', place: null },
  points: 2,
  change_bp: 6250,
};

const book: PriceBookDto = {
  inflation: {
    index_bp: 5625,
    items: [{ name: "Go'sht", change_bp: 6250, weight_bp: 5000 }],
    span_days: 1096,
  },
  streak_weeks: 2,
  best_streak_weeks: 3,
  logged_this_week: false,
};

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <PricesPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(commands.listPriceItems).mockResolvedValue({ status: 'ok', data: [meat] });
  vi.mocked(commands.priceBook).mockResolvedValue({ status: 'ok', data: book });
  vi.mocked(commands.addPrice).mockResolvedValue({ status: 'ok', data: null });
  vi.mocked(commands.addPriceItem).mockResolvedValue({ status: 'ok', data: null });
});

describe('PricesPage', () => {
  it('mahsulot o‘zgarishi, indeks va haftalik eslatma ko‘rsatiladi', async () => {
    renderPage();
    expect(await screen.findByTestId("change-Go'sht")).toHaveTextContent('+62,5%');
    expect(await screen.findByTestId('index-value')).toHaveTextContent('+56,25%');
    expect(screen.getByTestId('weekly')).toHaveTextContent('hali narx kiritmadingiz');
    expect(screen.getByTestId('weekly')).toHaveTextContent('Ketma-ket 2 hafta');
  });

  it('narx matni Rustga o‘zgartirilmay yuboriladi', async () => {
    renderPage();
    await userEvent.type(await screen.findByLabelText("Go'sht narxi"), '135 000');
    await userEvent.click(screen.getByRole('button', { name: 'Narx yozish' }));
    await waitFor(() => {
      expect(commands.addPrice).toHaveBeenCalledWith('m1', '135 000', null, null);
    });
  });

  it('yangi mahsulot og‘irligi foizdan bazis punktga o‘tadi', async () => {
    renderPage();
    await userEvent.type(await screen.findByRole('textbox', { name: 'Mahsulot' }), 'Non');
    await userEvent.click(screen.getByRole('button', { name: "Qo'shish" }));
    await waitFor(() => {
      expect(commands.addPriceItem).toHaveBeenCalledWith('Non', 'kg', 1000);
    });
  });

  it('«sichqon kemirgani» natijasi va keyingi qadam chiqadi', async () => {
    vi.mocked(commands.purchasingPower).mockResolvedValue({
      status: 'ok',
      data: {
        nominal: money("10 000 000 so'm"),
        real: money("6 575 162 so'm"),
        years: 3,
        annual_bp: 1500,
        example: {
          name: "Go'sht",
          unit: 'kg',
          price_today: money("130 000 so'm"),
          price_future: money("197 718 so'm"),
          quantity_now_milli: '76923',
          quantity_future_milli: '50577',
        },
      },
    });
    renderPage();
    await userEvent.type(
      await screen.findByLabelText('Taxminiy yillik narx o‘sishi (%)'.replace('‘', "'")),
      '15',
    );
    await userEvent.selectOptions(
      screen.getByLabelText('Mahsulot', { selector: 'select' }),
      "Go'sht",
    );
    await userEvent.click(screen.getByRole('button', { name: 'Hisoblash' }));
    const res = await screen.findByTestId('mouse-result');
    expect(res).toHaveTextContent("6 575 162 so'm");
    expect(res).toHaveTextContent('76,9 kg');
    expect(res).toHaveTextContent('50,5 kg');
    expect(commands.purchasingPower).toHaveBeenCalledWith('15', 3, 'm1');
    expect(
      screen.getByRole('button', { name: 'Kelajagimga o‘tish'.replace('‘', "'") }),
    ).toBeInTheDocument();
  });
});
