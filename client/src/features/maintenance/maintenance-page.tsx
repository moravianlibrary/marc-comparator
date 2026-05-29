import { useTranslation } from "react-i18next";
import {
  Trash2,
  BarChart3,
  Unlock,
  HardDrive,
  Search,
} from "lucide-react";
import { MaintenanceActionCard } from "./maintenance-action-card";

export function MaintenancePage() {
  const { t } = useTranslation("maintenance");

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MaintenanceActionCard
          icon={Trash2}
          titleKey="actions.delete-tasks.title"
          descriptionKey="actions.delete-tasks.description"
          endpoint="/maintenance/delete-tasks"
          showMaxAge
        />
        <MaintenanceActionCard
          icon={BarChart3}
          titleKey="actions.refresh-analytics.title"
          descriptionKey="actions.refresh-analytics.description"
          endpoint="/maintenance/refresh-analytics"
        />
        <MaintenanceActionCard
          icon={Unlock}
          titleKey="actions.cleanup-stale-locks.title"
          descriptionKey="actions.cleanup-stale-locks.description"
          endpoint="/maintenance/cleanup-stale-locks"
        />
        <MaintenanceActionCard
          icon={HardDrive}
          titleKey="actions.compact-sectors.title"
          descriptionKey="actions.compact-sectors.description"
          endpoint="/maintenance/compact-sectors"
        />
        <MaintenanceActionCard
          icon={Search}
          titleKey="actions.rebuild-search-vectors.title"
          descriptionKey="actions.rebuild-search-vectors.description"
          endpoint="/maintenance/rebuild-search-vectors"
        />
      </div>
    </div>
  );
}
