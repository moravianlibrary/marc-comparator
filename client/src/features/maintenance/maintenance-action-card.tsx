import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import apiClient from "@/lib/api-client";
import type { LucideIcon } from "lucide-react";

interface MaintenanceActionCardProps {
  icon: LucideIcon;
  titleKey: string;
  descriptionKey: string;
  endpoint: string;
  showMaxAge?: boolean;
}

export function MaintenanceActionCard({
  icon: Icon,
  titleKey,
  descriptionKey,
  endpoint,
  showMaxAge = false,
}: MaintenanceActionCardProps) {
  const { t } = useTranslation("maintenance");
  const [maxAgeDays, setMaxAgeDays] = useState<string>("");

  const mutation = useMutation({
    mutationFn: async () => {
      const body = showMaxAge && maxAgeDays
        ? { max_age_days: parseInt(maxAgeDays, 10) }
        : undefined;
      const { data } = await apiClient.post(endpoint, body);
      return data;
    },
    onSuccess: () => {
      toast.success(t("started"));
    },
    onError: () => {
      toast.error(t("common:error"));
    },
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">{t(titleKey)}</CardTitle>
        </div>
        <CardDescription>{t(descriptionKey)}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-3">
          {showMaxAge && (
            <div className="space-y-1">
              <Label htmlFor="max-age">{t("actions.delete-tasks.max-age-label")}</Label>
              <Input
                id="max-age"
                type="number"
                min={1}
                placeholder={t("actions.delete-tasks.max-age-placeholder")}
                value={maxAgeDays}
                onChange={(e) => setMaxAgeDays(e.target.value)}
                className="w-32"
              />
            </div>
          )}
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            size="sm"
          >
            {mutation.isPending ? t("running") : t("run")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
