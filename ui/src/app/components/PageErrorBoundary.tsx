import { Component, type ErrorInfo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { PrimaryButton } from "../finance/ui";

interface Props {
  /** Sahifa identifikatori: o'zgarsa, xato holati tozalanadi. */
  readonly resetKey: string;
  readonly children: ReactNode;
}

interface State {
  readonly failed: boolean;
}

/**
 * Sahifa darajasidagi error boundary: bitta sahifaning render xatosi butun ilovani bo'sh qoldirmasin.
 * Xato matni foydalanuvchiga ko'rsatilmaydi (unda ma'lumot bo'lishi mumkin); faqat umumiy xabar va
 * «qayta urinish». Boshqa sahifaga o'tilsa, holat o'zi tiklanadi.
 */
export class PageErrorBoundary extends Component<Props, State> {
  override state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    // Faqat ishlab chiqish konsoliga: summa yoki ism bo'lishi mumkin bo'lgan matn loglarga yozilmaydi.
    if (import.meta.env.DEV) {
      console.error("sahifa render xatosi", error, info.componentStack);
    }
  }

  override componentDidUpdate(previous: Props) {
    if (previous.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false });
    }
  }

  override render() {
    if (this.state.failed) {
      return (
        <CrashNotice
          onRetry={() => {
            this.setState({ failed: false });
          }}
        />
      );
    }
    return this.props.children;
  }
}

function CrashNotice({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="flex flex-col gap-4 rounded-xl border border-border bg-raised p-6">
      <h2 className="text-lg font-semibold text-text">{t("errors.pageCrashTitle")}</h2>
      <p className="text-sm text-muted">{t("errors.pageCrashBody")}</p>
      <div>
        <PrimaryButton onClick={onRetry}>{t("errors.pageCrashRetry")}</PrimaryButton>
      </div>
    </div>
  );
}
