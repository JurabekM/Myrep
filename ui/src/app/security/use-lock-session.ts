import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { commands } from "../../bindings/bindings";
import { SECURITY_STATUS_KEY } from "./security-status";

/** Bazani qulflaydi va holatni qayta yuklaydi: qulflash ekrani darhol ko'rinadi. */
export function useLockSession(): () => Promise<void> {
  const queryClient = useQueryClient();

  return useCallback(async () => {
    await commands.lock();
    await queryClient.invalidateQueries({ queryKey: SECURITY_STATUS_KEY });
  }, [queryClient]);
}
