import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";

export function LockBanner() {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState<string[]>([]);

  const { data: locks = [] } = useQuery<string[]>({
    queryKey: ["system", "locks"],
    queryFn: () => apiClient.get<string[]>("/system/locks").then((r) => r.data),
  });

  const visibleLocks = locks.filter((lock) => !dismissed.includes(lock));

  if (visibleLocks.length === 0) return null;

  return (
    <div className="bg-destructive/10 border-b border-destructive/20 px-6 py-2">
      {visibleLocks.map((lock) => (
        <div
          key={lock}
          className="flex items-center justify-between text-sm text-destructive"
        >
          <span>
            <span className="font-medium">
              {t("common:lock-banner.prefix")}
            </span>{" "}
            {lock}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => setDismissed((prev) => [...prev, lock])}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
    </div>
  );
}
