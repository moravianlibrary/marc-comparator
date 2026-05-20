import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import {
    useGetSettings,
    useGetSettingsZodSchema,
    useSetSettings,
} from "../hooks/useSettings";

const ValidatorsConfigPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "record-tools",
        "validators"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "record-tools",
        "validators"
    );
    const { mutate, isPending } = useSetSettings("record-tools", "validators");

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => mutate(data)}
            isSubmitting={isPending}
            i18nNamespace="validators-config"
        />
    );
};

export default ValidatorsConfigPage;
