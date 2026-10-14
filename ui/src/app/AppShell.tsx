import * as Tooltip from "@radix-ui/react-tooltip";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { HomePage } from "./pages/HomePage";
import { SettingsPage } from "./pages/SettingsPage";
import { Sidebar } from "./Sidebar";
import type { PageId } from "./navigation";
import { useLockSession } from "./security/use-lock-session";
import { useUiStore } from "./store";

/** Ilova qobig'i: chap navigatsiya, markazda ish maydoni, pastda ta'lim disklеymeri. */
export function AppShell() {
  const { t } = useTranslation();
  const page = useUiStore((state) => state.page);
  const lock = useLockSession();

  // Ctrl+L (macOS'da Cmd+L): daftarni darhol qulflaydi.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") {
        event.preventDefault();
        void lock();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [lock]);

  return (
    <Tooltip.Provider delayDuration={250}>
      <div className="flex h-full w-full">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <main id="main" className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl px-8 py-10">
              <CurrentPage page={page} />
            </div>
          </main>
          <footer className="border-t border-border px-8 py-2.5 text-xs text-subtle">
            {t("common.disclaimer")}
          </footer>
        </div>
      </div>
    </Tooltip.Provider>
  );
}

/** Faol sahifa. Hozircha faqat «Bosh sahifa» va «Sozlamalar» tayyor; qolganlari keyingi vazifalarda. */
function CurrentPage({ page }: { page: PageId }) {
  switch (page) {
    case "settings":
      return <SettingsPage />;
    default:
      return <HomePage />;
  }
}
