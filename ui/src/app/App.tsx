import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "./AppShell";
import { createQueryClient } from "./query-client";
import { SecurityGate } from "./security/SecurityGate";

/** Ildiz komponent: ma'lumot keshi, xavfsizlik darvozasi (PIN/qulflash) va ilova qobig'i. */
export function App() {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <SecurityGate>
        <AppShell />
      </SecurityGate>
    </QueryClientProvider>
  );
}
