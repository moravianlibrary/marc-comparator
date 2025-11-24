import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import {
    useGetSettings,
    useGetSettingsZodSchema,
    useSetSettings,
} from "../hooks/useSettings";

const CatalogSettingsPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "system",
        "catalog"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "system",
        "catalog"
    );
    const { mutate, isPending } = useSetSettings("system", "catalog");

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => mutate(data)}
            isSubmitting={isPending}
            title="Catalog Settings"
        />
    );
};

export default CatalogSettingsPage;
