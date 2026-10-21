import { useTranslation } from "react-i18next";

import { errorKey } from "../lib/api";

export function ErrorText({ error }: { error: unknown }) {
  const { t, i18n } = useTranslation();
  if (!error) return null;
  return (
    <p role="alert" className="text-sm text-danger">
      {t(errorKey(error, (k) => i18n.exists(k)))}
    </p>
  );
}
