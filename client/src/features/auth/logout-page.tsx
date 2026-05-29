import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLogout } from "@/hooks/use-auth";

export function LogoutPage() {
  const { t } = useTranslation("auth");
  const logout = useLogout();
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;
    logout.mutate();
  }, [logout]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-muted-foreground">{t("logging-out")}</div>
    </div>
  );
}
