import { QueryClient } from "@tanstack/react-query";

/**
 * Yadrodan keladigan ma'lumotlar uchun kesh (TanStack Query).
 * Mahalliy IPC qayta urinishni talab qilmaydi: xato darhol ko'rsatiladi.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  });
}
