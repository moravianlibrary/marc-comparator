import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

interface ApiErrorDetail {
  status: number;
  url: string;
  message: string;
  timestamp: string;
}

export function ApiErrorListener() {
  const { t } = useTranslation("errors");

  useEffect(() => {
    function handleApiError(e: Event) {
      const detail = (e as CustomEvent<ApiErrorDetail>).detail;
      const json = JSON.stringify(detail, null, 2);

      toast.error(t("api-error.title"), {
        duration: Infinity,
        description: (
          <div className="mt-2 space-y-2">
            <pre className="max-h-40 overflow-auto rounded bg-muted p-2 text-xs">
              {json}
            </pre>
            <button
              className="text-xs text-primary underline"
              onClick={() => {
                navigator.clipboard.writeText(json);
                toast.info(t("api-error.copied"));
              }}
            >
              {t("api-error.copy")}
            </button>
            <p className="text-xs text-muted-foreground">
              {t("api-error.contact-instructions")}
            </p>
          </div>
        ),
      });
    }

    window.addEventListener("api-error", handleApiError);
    return () => window.removeEventListener("api-error", handleApiError);
  }, [t]);

  return null;
}
