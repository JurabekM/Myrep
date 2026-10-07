import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import '../i18n';
import { App } from './App';

vi.mock('../bindings', () => ({
  commands: {
    allocateDemo: vi.fn(() =>
      Promise.resolve({
        status: 'ok',
        data: [{ minor: '70', currency: 'UZS', formatted: "0,70 so'm" }],
      }),
    ),
  },
}));

describe('App', () => {
  it("Rust'dan kelgan tayyor formatni ko'rsatadi", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: "Bo'lish" }));
    await waitFor(() => {
      expect(screen.getByText("0,70 so'm")).toBeInTheDocument();
    });
  });

  it("har bir ta'limiy ekranda disklеymer bor", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>,
    );
    expect(screen.getByText(/Fatvo yoki moliyaviy maslahat emas/)).toBeInTheDocument();
  });
});
