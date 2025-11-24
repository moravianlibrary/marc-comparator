import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import { useGetSettings, useGetSettingsZodSchema } from "../hooks/useSettings";

const TasksSettingsPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "system",
        "tasks"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "system",
        "tasks"
    );

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => console.log(data)}
            isSubmitting={false}
            title="Tasks Settings"
        />
    );
};

export default TasksSettingsPage;
