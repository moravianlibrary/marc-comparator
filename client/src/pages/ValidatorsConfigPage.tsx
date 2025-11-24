import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import { useGetSettings, useGetSettingsZodSchema } from "../hooks/useSettings";

const ValidatorsConfigPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "record-tools",
        "validators"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "record-tools",
        "validators"
    );

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => console.log(data)}
            isSubmitting={false}
            title="Validators Config"
        />
    );
};

export default ValidatorsConfigPage;
