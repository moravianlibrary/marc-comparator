import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLogout } from "@/hooks/use-auth";

export function LogoutPage() {
  const { t } = useTranslation("auth");
  const logout = useLogout();

  useEffect(() => {
    logout.mutate();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-muted-foreground">{t("logging-out")}</div>
    </div>
  );
}
