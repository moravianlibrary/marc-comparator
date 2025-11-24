import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import { useGetSettings, useGetSettingsZodSchema } from "../hooks/useSettings";

const CatalogSettingsPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "system",
        "catalog"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "system",
        "catalog"
    );

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => console.log(data)}
            isSubmitting={false}
            title="Catalog Settings"
        />
    );
};

export default CatalogSettingsPage;
