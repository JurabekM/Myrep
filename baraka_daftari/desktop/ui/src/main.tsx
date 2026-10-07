import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './app/App';
import { Gate } from './features/lock/Gate';
import './i18n';
import './index.css';

const queryClient = new QueryClient();
const root = document.getElementById('root');
if (!root) throw new Error('#root topilmadi');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Gate>
        <App />
      </Gate>
    </QueryClientProvider>
  </StrictMode>,
);
