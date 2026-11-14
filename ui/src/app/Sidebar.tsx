import { useTranslation } from "react-i18next";
import * as Tooltip from "@radix-ui/react-tooltip";
import { Lock } from "lucide-react";
import { BrandMark } from "./components/BrandMark";
import { LanguageToggle } from "./components/LanguageToggle";
import { NAV_ITEMS, type NavItem } from "./navigation";
import { useLockSession } from "./security/use-lock-session";
import { useUiStore } from "./store";

/** Chap navigatsiya paneli: brend, bo'limlar, qulflash va tilni almashtirish. */
export function Sidebar() {
  const { t } = useTranslation();
  const page = useUiStore((state) => state.page);
  const setPage = useUiStore((state) => state.setPage);
  const lock = useLockSession();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-3 px-5 pt-6 pb-5">
        <BrandMark className="size-8 shrink-0" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-text">{t("app.name")}</p>
          <p className="text-xs leading-snug text-subtle">{t("app.tagline")}</p>
        </div>
      </div>

      <nav aria-label={t("nav.label")} className="flex-1 overflow-y-auto px-3">
        <ul className="flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <NavButton
                item={item}
                active={item.id === page}
                onSelect={() => {
                  setPage(item.id);
                }}
              />
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex flex-col gap-3 border-t border-border p-4">
        <button
          type="button"
          onClick={() => {
            void lock();
          }}
          aria-keyshortcuts="Control+L"
          title={t("security.lockHint")}
          className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-sm text-muted transition-colors hover:bg-raised hover:text-text"
        >
          <Lock aria-hidden="true" className="size-4 shrink-0" />
          <span className="truncate">{t("security.lock")}</span>
        </button>
        <LanguageToggle compact />
      </div>
    </aside>
  );
}

interface NavButtonProps {
  item: NavItem;
  active: boolean;
  onSelect: () => void;
}

const NAV_BUTTON_BASE =
  "flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-sm transition-colors";

function NavButton({ item, active, onSelect }: NavButtonProps) {
  const { t } = useTranslation();
  const Icon = item.icon;
  const label = t(`nav.${item.id}`);

  if (item.enabled) {
    const stateClasses = active
      ? "bg-raised text-text"
      : "text-muted hover:bg-raised hover:text-text";

    return (
      <button
        type="button"
        onClick={onSelect}
        aria-current={active ? "page" : undefined}
        className={`${NAV_BUTTON_BASE} ${stateClasses}`}
      >
        <Icon aria-hidden="true" className="size-4 shrink-0" />
        <span className="truncate">{label}</span>
      </button>
    );
  }

  // Hali tayyor bo'lmagan bo'lim bosilmaydi; sababi tooltip'da ko'rsatiladi.
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          type="button"
          aria-disabled="true"
          className={`${NAV_BUTTON_BASE} cursor-not-allowed text-subtle`}
        >
          <Icon aria-hidden="true" className="size-4 shrink-0 opacity-60" />
          <span className="truncate">{label}</span>
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="right"
          sideOffset={8}
          className="rounded-md border border-border bg-raised px-2.5 py-1.5 text-xs text-text shadow-lg"
        >
          {t("common.comingSoon")}
          <Tooltip.Arrow className="fill-raised" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
