import { PluginHarvestSettingsForm } from './plugin-harvest-settings-form';
import { ScopedSettingsPage } from './scoped-settings-page';

export function PluginHarvestPage() {
  return (
    <ScopedSettingsPage scope="plugin-harvest">
      {props => <PluginHarvestSettingsForm {...props} />}
    </ScopedSettingsPage>
  );
}
