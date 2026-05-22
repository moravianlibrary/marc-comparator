import { useTranslation } from "react-i18next";
import { TypographyH3, TypographyP, TypographyList, TypographyCode } from "@/components/ui/typography";

export function CatalogHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.catalog.intro")}</TypographyP>
      <TypographyH3>{t("help.catalog.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("catalog.base")}</strong> — {t("help.catalog.base")}</li>
        <li><strong>{t("catalog.host")}</strong> — {t("help.catalog.host")}</li>
        <li><strong>{t("catalog.endpoint")}</strong> — {t("help.catalog.endpoint")}</li>
        <li><strong>{t("catalog.timeout")}</strong> — {t("help.catalog.timeout")}</li>
        <li><strong>{t("catalog.total-retry")}</strong> — {t("help.catalog.total-retry")}</li>
        <li><strong>{t("catalog.retry-backoff-factor")}</strong> — {t("help.catalog.retry-backoff-factor")}</li>
        <li><strong>{t("catalog.system-number-pattern")}</strong> — {t("help.catalog.system-number-pattern")}</li>
        <li><strong>{t("catalog.oai-identifier-template")}</strong> — {t("help.catalog.oai-identifier-template")}</li>
      </TypographyList>
    </>
  );
}

export function TasksHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.tasks.intro")}</TypographyP>
      <TypographyH3>{t("help.tasks.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("tasks-settings.progress-update-interval")}</strong> — {t("help.tasks.progress-update-interval")}</li>
      </TypographyList>
    </>
  );
}

export function AuthorityLinkersHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.authority-linkers.knihovny-cz.intro")}</TypographyP>
      <TypographyH3>{t("help.authority-linkers.knihovny-cz.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("authority-linkers.knihovny-cz.api-url")}</strong> — {t("help.authority-linkers.knihovny-cz.api-url")}</li>
        <li><strong>{t("authority-linkers.knihovny-cz.mappings")}</strong> — {t("help.authority-linkers.knihovny-cz.mappings")}</li>
      </TypographyList>
      <TypographyP>{t("help.authority-linkers.knihovny-cz.mapping-fields")}</TypographyP>
      <TypographyList>
        <li><strong>{t("authority-linkers.knihovny-cz.mapping-base")}</strong> — {t("help.authority-linkers.knihovny-cz.mapping-base")}</li>
        <li><strong>{t("authority-linkers.knihovny-cz.mapping-id-template")}</strong> — {t("help.authority-linkers.knihovny-cz.mapping-id-template")}</li>
        <li><strong>{t("authority-linkers.knihovny-cz.mapping-pattern")}</strong> — {t("help.authority-linkers.knihovny-cz.mapping-pattern")}</li>
      </TypographyList>
    </>
  );
}

export function ComparatorsHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.comparator.intro")}</TypographyP>
      <TypographyH3>{t("help.comparator.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("comparator.ollama-url")}</strong> — {t("help.comparator.ollama-url")}</li>
        <li><strong>{t("comparator.llm-enabled")}</strong> — {t("help.comparator.llm-enabled")}</li>
        <li><strong>{t("comparator.nonstandard-llm-enabled")}</strong> — {t("help.comparator.nonstandard-llm-enabled")}</li>
        <li><strong>{t("comparator.valid-threshold")}</strong> — {t("help.comparator.valid-threshold")}</li>
        <li><strong>{t("comparator.warning-threshold")}</strong> — {t("help.comparator.warning-threshold")}</li>
      </TypographyList>
      <TypographyP>
        {t("help.comparator.thresholds-note")}
      </TypographyP>
    </>
  );
}

export function ValidatorsHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.validators.kramerius-links.intro")}</TypographyP>
      <TypographyH3>{t("help.validators.kramerius-links.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("validators.kramerius-links.url-to-pid-pattern")}</strong> — {t("help.validators.kramerius-links.url-to-pid-pattern")}</li>
        <li><strong>{t("validators.kramerius-links.link-text-pattern")}</strong> — {t("help.validators.kramerius-links.link-text-pattern")}</li>
        <li><strong>{t("validators.kramerius-links.kramerius-host")}</strong> — {t("help.validators.kramerius-links.kramerius-host")}</li>
        <li><strong>{t("validators.kramerius-links.solr-cloud")}</strong> — {t("help.validators.kramerius-links.solr-cloud")}</li>
      </TypographyList>
    </>
  );
}

export function ProcessRecordsHelp() {
  const { t } = useTranslation("settings");
  return (
    <>
      <TypographyP>{t("help.process-records.intro")}</TypographyP>
      <TypographyH3>{t("help.process-records.fields-title")}</TypographyH3>
      <TypographyList>
        <li><strong>{t("process-records.target-bases")}</strong> — {t("help.process-records.target-bases")}</li>
        <li><strong>{t("process-records.authority-linkers")}</strong> — {t("help.process-records.authority-linkers")}</li>
        <li><strong>{t("process-records.comparator")}</strong> — {t("help.process-records.comparator")}</li>
        <li><strong>{t("process-records.validators")}</strong> — {t("help.process-records.validators")}</li>
      </TypographyList>
    </>
  );
}
