import { useTranslation } from 'react-i18next';
import { TypographyH3, TypographyList, TypographyP } from '@/components/ui/typography';

export function CatalogHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.catalog.intro')}</TypographyP>
      <TypographyH3>{t('help.catalog.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('catalog.base')}</strong> — {t('help.catalog.base')}
        </li>
        <li>
          <strong>{t('catalog.host')}</strong> — {t('help.catalog.host')}
        </li>
        <li>
          <strong>{t('catalog.endpoint')}</strong> — {t('help.catalog.endpoint')}
        </li>
        <li>
          <strong>{t('catalog.timeout')}</strong> — {t('help.catalog.timeout')}
        </li>
        <li>
          <strong>{t('catalog.total-retry')}</strong> — {t('help.catalog.total-retry')}
        </li>
        <li>
          <strong>{t('catalog.retry-backoff-factor')}</strong> —{' '}
          {t('help.catalog.retry-backoff-factor')}
        </li>
        <li>
          <strong>{t('catalog.system-number-pattern')}</strong> —{' '}
          {t('help.catalog.system-number-pattern')}
        </li>
        <li>
          <strong>{t('catalog.oai-sets')}</strong> — {t('help.catalog.oai-sets')}
        </li>
        <li>
          <strong>{t('catalog.oai-identifier-template')}</strong> —{' '}
          {t('help.catalog.oai-identifier-template')}
        </li>
      </TypographyList>
    </>
  );
}

export function TasksHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.tasks.intro')}</TypographyP>
      <TypographyH3>{t('help.tasks.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('tasks-settings.progress-update-interval')}</strong> —{' '}
          {t('help.tasks.progress-update-interval')}
        </li>
        <li>
          <strong>{t('tasks-settings.commit-interval')}</strong> — {t('help.tasks.commit-interval')}
        </li>
        <li>
          <strong>{t('tasks-settings.analytics-rebuild-interval')}</strong> —{' '}
          {t('help.tasks.analytics-rebuild-interval')}
        </li>
      </TypographyList>
    </>
  );
}

export function LinkingDecisionHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.authority-linkers.decision.intro')}</TypographyP>
      <TypographyP>{t('help.authority-linkers.decision.two-stages')}</TypographyP>
      <TypographyH3>{t('help.authority-linkers.decision.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('authority-linkers.decision.confident-threshold')}</strong> —{' '}
          {t('help.authority-linkers.decision.confident-threshold')}
        </li>
        <li>
          <strong>{t('authority-linkers.decision.candidate-margin')}</strong> —{' '}
          {t('help.authority-linkers.decision.candidate-margin')}
        </li>
      </TypographyList>
    </>
  );
}

export function PeriodicSyncHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.periodic-sync.intro')}</TypographyP>
      <TypographyP>{t('help.periodic-sync.processing-follows')}</TypographyP>
      <TypographyH3>{t('help.periodic-sync.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('periodic-sync.enabled')}</strong> — {t('help.periodic-sync.enabled')}
        </li>
        <li>
          <strong>{t('cron.label')}</strong> — {t('help.periodic-sync.cron')}
        </li>
      </TypographyList>
    </>
  );
}

export function AuthorityLinkersHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.authority-linkers.knihovny-cz.intro')}</TypographyP>
      <TypographyP>{t('help.authority-linkers.knihovny-cz.how-it-matches')}</TypographyP>
      <TypographyH3>{t('help.authority-linkers.knihovny-cz.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.api-url')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.api-url')}
        </li>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.minimum-confidence')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.minimum-confidence')}
        </li>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.mappings')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.mappings')}
        </li>
      </TypographyList>
      <TypographyP>{t('help.authority-linkers.knihovny-cz.mapping-fields')}</TypographyP>
      <TypographyList>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.mapping-base')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.mapping-base')}
        </li>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.mapping-id-template')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.mapping-id-template')}
        </li>
        <li>
          <strong>{t('authority-linkers.knihovny-cz.mapping-pattern')}</strong> —{' '}
          {t('help.authority-linkers.knihovny-cz.mapping-pattern')}
        </li>
      </TypographyList>
    </>
  );
}

export function MarcXmlDumpLinkerHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.authority-linkers.marcxml-dump.intro')}</TypographyP>
      <TypographyP>{t('help.authority-linkers.marcxml-dump.format-note')}</TypographyP>
      <TypographyP>{t('help.authority-linkers.marcxml-dump.how-it-matches')}</TypographyP>
      <TypographyP>{t('help.authority-linkers.marcxml-dump.needs-harvest')}</TypographyP>
      <TypographyH3>{t('help.authority-linkers.marcxml-dump.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.dump-url')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.dump-url')}
        </li>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.target-base')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.target-base')}
        </li>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.system-number-tag')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.system-number')}
        </li>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.identifier-minimum-confidence')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.identifier-minimum-confidence')}
        </li>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.title-minimum-confidence')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.title-minimum-confidence')}
        </li>
        <li>
          <strong>{t('authority-linkers.marcxml-dump.candidate-limit')}</strong> —{' '}
          {t('help.authority-linkers.marcxml-dump.candidate-limit')}
        </li>
      </TypographyList>
    </>
  );
}

export function ComparatorsHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.comparator.intro')}</TypographyP>
      <TypographyH3>{t('help.comparator.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('comparator.ollama-url')}</strong> — {t('help.comparator.ollama-url')}
        </li>
        <li>
          <strong>{t('comparator.llm-enabled')}</strong> — {t('help.comparator.llm-enabled')}
        </li>
        <li>
          <strong>{t('comparator.nonstandard-llm-enabled')}</strong> —{' '}
          {t('help.comparator.nonstandard-llm-enabled')}
        </li>
        <li>
          <strong>{t('comparator.excellent-threshold')}</strong> —{' '}
          {t('help.comparator.excellent-threshold')}
        </li>
        <li>
          <strong>{t('comparator.moderate-threshold')}</strong> —{' '}
          {t('help.comparator.moderate-threshold')}
        </li>
      </TypographyList>
      <TypographyH3>{t('help.comparator.scoring-title')}</TypographyH3>
      <TypographyP>{t('help.comparator.scoring-intro')}</TypographyP>
      <TypographyList>
        <li>{t('help.comparator.scoring-step-1')}</li>
        <li>{t('help.comparator.scoring-step-2')}</li>
        <li>{t('help.comparator.scoring-step-3')}</li>
      </TypographyList>
      <TypographyH3>{t('help.comparator.normalization-title')}</TypographyH3>
      <TypographyP>{t('help.comparator.normalization-intro')}</TypographyP>
      <TypographyList>
        <li>
          <strong>Excellent (0.9–1.0)</strong> — {t('help.comparator.normalization-excellent')}
        </li>
        <li>
          <strong>Moderate (0.7–0.9)</strong> — {t('help.comparator.normalization-moderate')}
        </li>
        <li>
          <strong>Poor (0.0–0.7)</strong> — {t('help.comparator.normalization-poor')}
        </li>
      </TypographyList>
    </>
  );
}

export function ValidatorsHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.validators.kramerius-links.intro')}</TypographyP>
      <TypographyH3>{t('help.validators.kramerius-links.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('validators.kramerius-links.url-to-pid-pattern')}</strong> —{' '}
          {t('help.validators.kramerius-links.url-to-pid-pattern')}
        </li>
        <li>
          <strong>{t('validators.kramerius-links.url-to-pid-wrong-path-pattern')}</strong> —{' '}
          {t('help.validators.kramerius-links.url-to-pid-wrong-path-pattern')}
        </li>
        <li>
          <strong>{t('validators.kramerius-links.url-to-pid-fallback-pattern')}</strong> —{' '}
          {t('help.validators.kramerius-links.url-to-pid-fallback-pattern')}
        </li>
        <li>
          <strong>{t('validators.kramerius-links.link-text-pattern')}</strong> —{' '}
          {t('help.validators.kramerius-links.link-text-pattern')}
        </li>
        <li>
          <strong>{t('validators.kramerius-links.kramerius-host')}</strong> —{' '}
          {t('help.validators.kramerius-links.kramerius-host')}
        </li>
        <li>
          <strong>{t('validators.kramerius-links.solr-cloud')}</strong> —{' '}
          {t('help.validators.kramerius-links.solr-cloud')}
        </li>
      </TypographyList>
    </>
  );
}

export function MaintenanceHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.maintenance.intro')}</TypographyP>
      <TypographyH3>{t('help.maintenance.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('maintenance.enabled')}</strong> — {t('help.maintenance.enabled')}
        </li>
        <li>
          <strong>{t('cron.label')}</strong> — {t('help.maintenance.cron')}
        </li>
        <li>
          <strong>{t('maintenance.max-age-days')}</strong> — {t('help.maintenance.max-age-days')}
        </li>
      </TypographyList>
    </>
  );
}

export function ProcessRecordsHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.process-records.intro')}</TypographyP>
      <TypographyH3>{t('help.process-records.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('process-records.target-bases')}</strong> —{' '}
          {t('help.process-records.target-bases')}
        </li>
        <li>
          <strong>{t('process-records.authority-linkers')}</strong> —{' '}
          {t('help.process-records.authority-linkers')}
        </li>
        <li>
          <strong>{t('process-records.validators')}</strong> —{' '}
          {t('help.process-records.validators')}
        </li>
      </TypographyList>
    </>
  );
}

export function PluginHarvestHelp() {
  const { t } = useTranslation('settings');
  return (
    <>
      <TypographyP>{t('help.plugin-harvest.intro')}</TypographyP>
      <TypographyP>{t('help.plugin-harvest.not-catalog-sync')}</TypographyP>
      <TypographyH3>{t('help.plugin-harvest.fields-title')}</TypographyH3>
      <TypographyList>
        <li>
          <strong>{t('plugin-harvest.enabled')}</strong> — {t('help.plugin-harvest.enabled')}
        </li>
        <li>
          <strong>{t('cron.label')}</strong> — {t('help.plugin-harvest.cron')}
        </li>
        <li>
          <strong>{t('plugin-harvest.ready')}</strong> — {t('help.plugin-harvest.ready')}
        </li>
        <li>
          <strong>{t('plugin-harvest.last-records')}</strong> —{' '}
          {t('help.plugin-harvest.last-records')}
        </li>
        <li>
          <strong>{t('plugin-harvest.run')}</strong> — {t('help.plugin-harvest.run')}
        </li>
        <li>
          <strong>{t('plugin-harvest.full-rebuild')}</strong> —{' '}
          {t('help.plugin-harvest.full-rebuild')}
        </li>
      </TypographyList>
    </>
  );
}
