import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './app/App';
import { Gate } from './features/lock/Gate';
import { QuickExpenseWindow } from './features/quick/QuickExpenseWindow';
import './i18n';
import './index.css';

const queryClient = new QueryClient();
const root = document.getElementById('root');
if (!root) throw new Error('#root topilmadi');

// Tray / Ctrl+Alt+B oynasi o'z holatini o'zi boshqaradi (qulfda hech narsa ko'rsatmaydi).
const isQuick = new URLSearchParams(window.location.search).get('window') === 'quick';

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {isQuick ? (
        <QuickExpenseWindow />
      ) : (
        <Gate>
          <App />
        </Gate>
      )}
    </QueryClientProvider>
  </StrictMode>,
);
