import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  TypographyH3,
  TypographyP,
  TypographyList,
  TypographyMuted,
} from "@/components/ui/typography";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import type { PermissionGuard } from "@/types/permission";

interface Props {
  open: boolean;
  onClose: () => void;
}

function SubSection({
  title,
  description,
  tips,
}: {
  title: string;
  description: string;
  tips?: string[];
}) {
  return (
    <div className="mt-3">
      <TypographyMuted className="font-medium text-foreground">{title}</TypographyMuted>
      <TypographyP>{description}</TypographyP>
      {tips && tips.length > 0 && (
        <TypographyList>
          {tips.map((tip, i) => (
            <li key={i}>{tip}</li>
          ))}
        </TypographyList>
      )}
    </div>
  );
}

interface HelpSection {
  permission?: PermissionGuard;
  render: () => ReactNode;
}

export function HelpDialog({ open, onClose }: Props) {
  const { t } = useTranslation("common");
  const { hasPermission } = useHasPermission();

  const tList = (key: string): string[] => {
    const val = t(key, { returnObjects: true });
    return Array.isArray(val) ? (val as string[]) : [];
  };

  const sections: HelpSection[] = [
    // About — always visible
    {
      render: () => (
        <section>
          <TypographyH3>{t("help.about.title")}</TypographyH3>
          <TypographyP>{t("help.about.description")}</TypographyP>
        </section>
      ),
    },
    // Workflow — always visible
    {
      render: () => (
        <section>
          <TypographyH3>{t("help.workflow.title")}</TypographyH3>
          <TypographyP>{t("help.workflow.intro")}</TypographyP>
          <TypographyList>
            {tList("help.workflow.steps").map((step, i) => (
              <li key={i}>
                <strong>{i + 1}.</strong> {step}
              </li>
            ))}
          </TypographyList>
        </section>
      ),
    },
    // Records (filtering, table, detail) — ReadRecords
    {
      permission: Permission.ReadRecords,
      render: () => (
        <section>
          <TypographyH3>{t("help.records.title")}</TypographyH3>
          <TypographyP>{t("help.records.intro")}</TypographyP>
          <SubSection
            title={t("help.records.filtering.title")}
            description={t("help.records.filtering.description")}
            tips={tList("help.records.filtering.tips")}
          />
          <SubSection
            title={t("help.records.table.title")}
            description={t("help.records.table.description")}
            tips={tList("help.records.table.tips")}
          />
          <SubSection
            title={t("help.records.detail.title")}
            description={t("help.records.detail.description")}
            tips={tList("help.records.detail.tips")}
          />
          {hasPermission({ any: [Permission.AddRecords, Permission.SyncRecordsFromCatalog] }) !==
            false && (
            <SubSection
              title={t("help.records.addition.title")}
              description={t("help.records.addition.description")}
              tips={tList("help.records.addition.tips")}
            />
          )}
        </section>
      ),
    },
    // Review — ReviewRecords
    {
      permission: Permission.ReviewRecords,
      render: () => (
        <section>
          <TypographyH3>{t("help.review.title")}</TypographyH3>
          <TypographyP>{t("help.review.description")}</TypographyP>
          <TypographyList>
            {tList("help.review.tips").map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </TypographyList>
        </section>
      ),
    },
    // Tasks — ManageTasks
    {
      permission: Permission.ManageTasks,
      render: () => (
        <section>
          <TypographyH3>{t("help.tasks.title")}</TypographyH3>
          <TypographyP>{t("help.tasks.description")}</TypographyP>
          <TypographyList>
            {tList("help.tasks.tips").map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </TypographyList>
        </section>
      ),
    },
    // Settings — ManageAppSettings or ManageTaskSettings
    {
      permission: { any: [Permission.ManageAppSettings, Permission.ManageTaskSettings] },
      render: () => (
        <section>
          <TypographyH3>{t("help.settings.title")}</TypographyH3>
          <TypographyP>{t("help.settings.description")}</TypographyP>
          <TypographyList>
            {tList("help.settings.sections").map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </TypographyList>
        </section>
      ),
    },
    // Access control — ManageAccessControl
    {
      permission: Permission.ManageAccessControl,
      render: () => (
        <section>
          <TypographyH3>{t("help.access-control.title")}</TypographyH3>
          <TypographyP>{t("help.access-control.description")}</TypographyP>
        </section>
      ),
    },
    // Maintenance — ManageAppSettings
    {
      permission: Permission.ManageAppSettings,
      render: () => (
        <section>
          <TypographyH3>{t("help.maintenance.title")}</TypographyH3>
          <TypographyP>{t("help.maintenance.description")}</TypographyP>
          <TypographyList>
            {tList("help.maintenance.actions").map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </TypographyList>
        </section>
      ),
    },
    // Shortcuts — always visible
    {
      render: () => (
        <section>
          <TypographyH3>{t("help.shortcuts.title")}</TypographyH3>
          <TypographyList>
            {tList("help.shortcuts.items").map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </TypographyList>
        </section>
      ),
    },
  ];

  const visible = sections.filter((s) => !s.permission || hasPermission(s.permission) !== false);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="min-w-[60vw] max-w-[90vw] max-h-[80vh] p-0">
        <DialogHeader className="px-6 pt-6">
          <DialogTitle>{t("menu.help")}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="px-6 pb-6 max-h-[calc(80vh-4rem)]">
          <div className="space-y-6">
            {visible.map((s, i) => (
              <div key={i}>
                {i > 0 && <Separator className="mb-6" />}
                {s.render()}
              </div>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
