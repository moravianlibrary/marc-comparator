import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

const emails = (import.meta.env.VITE_ADMIN_EMAILS || "")
  .split(",")
  .filter(Boolean);

export function ServiceUnavailablePage() {
  const { t } = useTranslation("errors");
  const [searchParams] = useSearchParams();
  const [checking, setChecking] = useState(false);
  const [stillDown, setStillDown] = useState(false);

  const redirect = searchParams.get("redirect") || "/";

  async function handleTryAgain() {
    setChecking(true);
    setStillDown(false);
    try {
      const response = await axios.get("/api/system/health", { timeout: 3000 });
      if (response.status === 200) {
        window.location.href = redirect;
        return;
      }
    } catch {
      // backend still down
    }
    setChecking(false);
    setStillDown(true);
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="mx-auto max-w-md space-y-6 text-center">
        <h1 className="text-2xl font-semibold">
          {t("service-unavailable.title")}
        </h1>
        <p className="text-muted-foreground">
          {t("service-unavailable.message")}
        </p>

        {emails.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              {t("service-unavailable.contact-prefix")}
            </p>
            <div className="flex flex-col items-center gap-1">
              {emails.map((email) => (
                <a
                  key={email}
                  href={`mailto:${email}`}
                  className="text-sm text-primary underline"
                >
                  {email}
                </a>
              ))}
            </div>
          </div>
        )}

        <Button onClick={handleTryAgain} disabled={checking}>
          {checking && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t("service-unavailable.try-again")}
        </Button>

        {stillDown && (
          <p className="text-sm text-destructive">
            {t("service-unavailable.still-down")}
          </p>
        )}
      </div>
    </div>
  );
}
