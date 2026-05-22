import { useTranslation } from "react-i18next";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import { FetchSingleForm } from "./fetch-single-form";
import { FetchBatchForm } from "./fetch-batch-form";
import { SyncForm } from "./sync-form";

export function AdditionView() {
  const { t } = useTranslation("records");
  const { hasPermission } = useHasPermission();
  const canAdd = hasPermission(Permission.AddRecords);
  const canSync = hasPermission(Permission.SyncRecordsFromCatalog);

  if (!canAdd && !canSync) {
    return null;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t("addition.title")}</h2>
      {canAdd && <FetchSingleForm />}
      {canAdd && <FetchBatchForm />}
      {canSync && <SyncForm />}
    </div>
  );
}
