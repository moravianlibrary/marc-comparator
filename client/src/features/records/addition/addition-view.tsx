import { useTranslation } from "react-i18next";
import { FetchSingleForm } from "./fetch-single-form";
import { FetchBatchForm } from "./fetch-batch-form";
import { SyncForm } from "./sync-form";

export function AdditionView() {
  const { t } = useTranslation("records");

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{t("addition.title")}</h2>
      <FetchSingleForm />
      <FetchBatchForm />
      <SyncForm />
    </div>
  );
}
