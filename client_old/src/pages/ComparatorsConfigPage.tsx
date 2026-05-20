import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import {
    useGetSettings,
    useGetSettingsZodSchema,
    useSetSettings,
} from "../hooks/useSettings";

const ComparatorsConfigPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "record-tools",
        "comparators"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "record-tools",
        "comparators"
    );
    const { mutate, isPending } = useSetSettings("record-tools", "comparators");

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => mutate(data)}
            isSubmitting={isPending}
            i18nNamespace="comparators-config"
        />
    );
};

export default ComparatorsConfigPage;
