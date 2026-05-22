import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  TypographyH3,
  TypographyP,
  TypographyList,
  TypographyMuted,
} from "@/components/ui/typography";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function HelpDialog({ open, onClose }: Props) {
  const { t } = useTranslation();
  const ts = (key: string) => t(key, { ns: "settings" });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="min-w-[60vw] max-w-[90vw] max-h-[80vh] p-0">
        <DialogHeader className="px-6 pt-6">
          <DialogTitle>{t("common:menu.help")}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="px-6 pb-6 max-h-[calc(80vh-4rem)]">
          <div className="space-y-6">
            {/* About */}
            <section>
              <TypographyH3>{t("common:app-name")}</TypographyH3>
              <TypographyP>{t("auth:about-app")}</TypographyP>
            </section>

            <Separator />

            {/* Workflow */}
            <section>
              <TypographyH3>{ts("help.title")}</TypographyH3>
              <TypographyP>{ts("help.process-records.intro")}</TypographyP>
              <TypographyList>
                <li>
                  <strong>{ts("process-records.authority-linkers")}</strong>
                  {" \u2014 "}
                  {ts("help.process-records.authority-linkers")}
                </li>
                <li>
                  <strong>{ts("process-records.comparator")}</strong>
                  {" \u2014 "}
                  {ts("help.process-records.comparator")}
                </li>
                <li>
                  <strong>{ts("process-records.validators")}</strong>
                  {" \u2014 "}
                  {ts("help.process-records.validators")}
                </li>
              </TypographyList>
            </section>

            <Separator />

            {/* Authority linkers */}
            <section>
              <TypographyH3>
                {ts("types.authority-linkers")}
              </TypographyH3>

              <div className="mt-3">
                <TypographyMuted className="font-medium text-foreground">
                  {ts("authority-linkers.knihovny-cz.title")}
                </TypographyMuted>
                <TypographyP>
                  {ts("help.authority-linkers.knihovny-cz.intro")}
                </TypographyP>
              </div>
            </section>

            <Separator />

            {/* Comparator */}
            <section>
              <TypographyH3>{ts("types.comparators")}</TypographyH3>

              <div className="mt-3">
                <TypographyMuted className="font-medium text-foreground">
                  {ts("comparator.title")}
                </TypographyMuted>
                <TypographyP>
                  {ts("help.comparator.intro")}
                </TypographyP>
                <TypographyList>
                  <li>
                    <strong>{ts("comparator.valid-threshold")}</strong>
                    {" \u2014 "}
                    {ts("help.comparator.valid-threshold")}
                  </li>
                  <li>
                    <strong>{ts("comparator.warning-threshold")}</strong>
                    {" \u2014 "}
                    {ts("help.comparator.warning-threshold")}
                  </li>
                </TypographyList>
                <TypographyMuted>
                  {ts("help.comparator.thresholds-note")}
                </TypographyMuted>
              </div>
            </section>

            <Separator />

            {/* Validators */}
            <section>
              <TypographyH3>{ts("types.validators")}</TypographyH3>

              <div className="mt-3">
                <TypographyMuted className="font-medium text-foreground">
                  {ts("validators.kramerius-links.title")}
                </TypographyMuted>
                <TypographyP>
                  {ts("help.validators.kramerius-links.intro")}
                </TypographyP>
              </div>
            </section>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
