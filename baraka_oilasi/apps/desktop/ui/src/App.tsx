import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { commands, events } from "./bindings";
import { Shell } from "./components/Shell";
import { LockScreen } from "./features/lock/LockScreen";
import { SetupScreen } from "./features/setup/SetupScreen";
import { call } from "./lib/api";
import { keys, resetAfterLock } from "./lib/queryClient";

export function App() {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: keys.session, queryFn: () => call(commands.sessionStatus()) });

  useEffect(() => {
    // Yadrodagi o'zgarish → tegishli so'rovlarni qayta o'qish; avto-qulf → summalarni tozalash.
    const changed = events.coreChanged.listen(() => void qc.invalidateQueries());
    const locked = events.sessionLocked.listen(() => resetAfterLock(qc));
    return () => {
      void changed.then((off) => off());
      void locked.then((off) => off());
    };
  }, [qc]);

  if (!status.data) return null;
  if (!status.data.initialized) return <SetupScreen />;
  if (!status.data.unlocked) return <LockScreen lockedUntil={status.data.lockedUntil} />;
  return <Shell />;
}
