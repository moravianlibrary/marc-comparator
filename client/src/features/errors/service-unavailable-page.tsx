import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

const emails = (import.meta.env.VITE_ADMIN_EMAILS || "")
  .split(",")
  .filter(Boolean);

export function ServiceUnavailablePage() {
  const { t } = useTranslation("errors");

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

        <Button onClick={() => window.location.reload()}>
          {t("service-unavailable.try-again")}
        </Button>
      </div>
    </div>
  );
}
