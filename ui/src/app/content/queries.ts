import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { commands } from "../../bindings/bindings";
import { unwrap } from "../finance/command-error";

/** Boblar kontenti keshlari. Barchasi `content` prefiksi bilan: vazifa o'zgarsa, hammasi yangilanadi. */
export const contentKeys = {
  all: ["content"] as const,
  chapters: ["content", "chapters"] as const,
  chapter: (chapterId: string) => ["content", "chapter", chapterId] as const,
  weekly: ["content", "weekly"] as const,
};

/** Vazifa yoki «Daftar sahifasi» o'zgarganda barcha kontent keshlarini qayta yuklaydi. */
export function useInvalidateContent(): () => Promise<void> {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: contentKeys.all });
  }, [queryClient]);
}

/** Har bir so'rov uchun bir xil: IPC natijasi qiymatga aylanadi, xato — `CommandError`. */
export const contentFetchers = {
  chapters: () => commands.listChapters().then(unwrap),
  chapter: (chapterId: string) => commands.getChapter(chapterId).then(unwrap),
  weekly: () => commands.getWeeklyTasks().then(unwrap),
};
