import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "./AppShell";
import { createQueryClient } from "./query-client";
import { QuickWindow } from "./quick/QuickWindow";
import { SecurityGate } from "./security/SecurityGate";
import { QUICK_WINDOW_LABEL, currentWindowLabel } from "./window-label";

/**
 * Ildiz komponent: ma'lumot keshi, xavfsizlik darvozasi (PIN/qulflash) va ilova qobig'i.
 * «Tez xarajat» mini oynasi (yorliq `quick`) o'z ekranini ko'rsatadi: qulf holatida summasiz.
 */
export function App() {
  const [queryClient] = useState(createQueryClient);
  const [label] = useState(currentWindowLabel);

  if (label === QUICK_WINDOW_LABEL) {
    return (
      <QueryClientProvider client={queryClient}>
        <QuickWindow />
      </QueryClientProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SecurityGate>
        <AppShell />
      </SecurityGate>
    </QueryClientProvider>
  );
}
