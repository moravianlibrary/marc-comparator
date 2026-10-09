import { PeriodicSyncSettingsForm } from './periodic-sync-settings-form';
import { ScopedSettingsPage } from './scoped-settings-page';

export function PeriodicSyncPage() {
  return (
    <ScopedSettingsPage scope="periodic-sync">
      {props => <PeriodicSyncSettingsForm {...props} />}
    </ScopedSettingsPage>
  );
}
