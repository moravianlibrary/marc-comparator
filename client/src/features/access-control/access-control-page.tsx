import { useTranslation } from "react-i18next";
import { Separator } from "@/components/ui/separator";
import { RolesSection } from "./roles-section";
import { UsersSection } from "./users-section";

export function AccessControlPage() {
  const { t } = useTranslation("access-control");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <RolesSection />
      <Separator />
      <UsersSection />
    </div>
  );
}
