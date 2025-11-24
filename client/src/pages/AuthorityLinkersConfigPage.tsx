import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import { useGetSettings, useGetSettingsZodSchema } from "../hooks/useSettings";

const AuthorityLinkersConfigPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "record-tools",
        "authority-linkers"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "record-tools",
        "authority-linkers"
    );

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => console.log(data)}
            isSubmitting={false}
            title="Authority Linkers Config"
        />
    );
};

export default AuthorityLinkersConfigPage;
