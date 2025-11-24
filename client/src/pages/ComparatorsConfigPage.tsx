import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import { useGetSettings, useGetSettingsZodSchema } from "../hooks/useSettings";

const ComparatorsConfigPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "record-tools",
        "comparators"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "record-tools",
        "comparators"
    );

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => console.log(data)}
            isSubmitting={false}
            title="Comparators Config"
        />
    );
};

export default ComparatorsConfigPage;
