import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "./AppShell";
import { createQueryClient } from "./query-client";

/** Ildiz komponent: ma'lumot keshi va ilova qobig'i. */
export function App() {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
