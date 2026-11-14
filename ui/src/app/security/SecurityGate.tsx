import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { LockScreen } from "./LockScreen";
import { SetupScreen } from "./SetupScreen";
import { SECURITY_STATUS_KEY, STATUS_POLL_MS, fetchSecurityStatus } from "./security-status";

/**
 * Xavfsizlik darvozasi: avval PIN o'rnatilganini, keyin bazaning ochiq ekanini tekshiradi.
 * Ilovaning asosiy qismi faqat baza ochiq bo'lganda ko'rinadi.
 */
export function SecurityGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const status = useQuery({
    queryKey: SECURITY_STATUS_KEY,
    queryFn: fetchSecurityStatus,
    // Ochiq holatda avto-qulflash backend'da bajariladi; UI uni shu so'rov orqali ko'radi.
    refetchInterval: (query) => (query.state.data?.unlocked ? STATUS_POLL_MS : false),
  });

  if (status.isPending) {
    return <p className="p-8 text-sm text-muted">{t("common.loading")}</p>;
  }

  if (status.isError) {
    return (
      <p role="alert" className="p-8 text-sm text-danger">
        {t("security.statusError")}
      </p>
    );
  }

  if (!status.data.setUp) {
    return <SetupScreen />;
  }

  if (!status.data.unlocked) {
    return <LockScreen />;
  }

  return <>{children}</>;
}
