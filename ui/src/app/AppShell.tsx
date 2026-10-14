import * as Tooltip from "@radix-ui/react-tooltip";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AuditPage } from "./pages/AuditPage";
import { ChaptersPage } from "./pages/ChaptersPage";
import { HomePage } from "./pages/HomePage";
import { IncomePage } from "./pages/IncomePage";
import { ObligationsPage } from "./pages/ObligationsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VaultPage } from "./pages/VaultPage";
import { WhoseMoneyPage } from "./pages/WhoseMoneyPage";
import { QuickEntry } from "./finance/QuickEntry";
import { Sidebar } from "./Sidebar";
import type { PageId } from "./navigation";
import { useLockSession } from "./security/use-lock-session";
import { useUiStore } from "./store";

/** Ilova qobig'i: chap navigatsiya, markazda ish maydoni, pastda ta'lim disklеymeri. */
export function AppShell() {
  const { t } = useTranslation();
  const page = useUiStore((state) => state.page);
  const quickEntryOpen = useUiStore((state) => state.quickEntryOpen);
  const setQuickEntryOpen = useUiStore((state) => state.setQuickEntryOpen);
  const lock = useLockSession();

  // Ctrl+L (macOS'da Cmd+L): daftarni darhol qulflaydi. Ctrl+N: tez daromad kiritish.
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey)) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === "l") {
        event.preventDefault();
        void lock();
      } else if (key === "n") {
        event.preventDefault();
        setQuickEntryOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [lock, setQuickEntryOpen]);

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
      {quickEntryOpen ? (
        <QuickEntry
          onClose={() => {
            setQuickEntryOpen(false);
          }}
        />
      ) : null}
    </Tooltip.Provider>
  );
}

/** Faol sahifa. Bosh sahifa, daromad, «Kelajagim», audit, «Kimning puli?», majburiyat va sozlamalar. */
function CurrentPage({ page }: { page: PageId }) {
  switch (page) {
    case "income":
      return <IncomePage />;
    case "future":
      return <VaultPage />;
    case "audit":
      return <AuditPage />;
    case "whose-money":
      return <WhoseMoneyPage />;
    case "obligations":
      return <ObligationsPage />;
    case "chapters":
      return <ChaptersPage />;
    case "settings":
      return <SettingsPage />;
    default:
      return <HomePage />;
  }
}
