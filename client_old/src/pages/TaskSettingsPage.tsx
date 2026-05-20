import type { ReactElement } from "react";
import ZodFormPageLayout from "../components/templates/ZodFormPageLayout";
import {
    useGetSettings,
    useGetSettingsZodSchema,
    useSetSettings,
} from "../hooks/useSettings";

const TasksSettingsPage = (): ReactElement => {
    const { zodSchema, isLoading: isLoadingSchema } = useGetSettingsZodSchema(
        "system",
        "tasks"
    );
    const { data: settings, isLoading: isLoadingSettings } = useGetSettings(
        "system",
        "tasks"
    );
    const { mutate, isPending } = useSetSettings("system", "tasks");

    return (
        <ZodFormPageLayout
            schema={zodSchema}
            initValues={settings}
            isLoading={isLoadingSchema || isLoadingSettings}
            onSubmit={(data) => mutate(data)}
            isSubmitting={isPending}
            i18nNamespace="tasks-settings"
        />
    );
};

export default TasksSettingsPage;
