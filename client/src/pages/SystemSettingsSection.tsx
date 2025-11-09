import { useState, useEffect, type ReactElement, Fragment } from "react";
import {
    useGetSettingsSchema,
    useGetSettings,
    useSetSettings,
} from "../hooks/useSettings";
import { Content, PageGroup, PageSection } from "@patternfly/react-core";
import type { Settings } from "../models/api/responses/settings";
import SettingsTable from "../components/organisms/SettingsTable";

const SystemSettingsSection = (): ReactElement => {
    const { data: catalogSchema, isLoading: catalogSchemaLoading } =
        useGetSettingsSchema("system", "catalog");

    const { data: catalogSettings, isLoading: catalogSettingsLoading } =
        useGetSettings("system", "catalog");

    const [catalogSettingsEdit, setCatalogSettingsEdit] = useState<
        Settings | undefined
    >(catalogSettings);

    // useEffect(() => {
    //     if (settings) setEditableSettings(settings);
    // }, [settings]);

    // const setSettingsMutation = useSetSettings(domain, scope, editableSettings);

    if (catalogSchemaLoading || catalogSettingsLoading)
        return <div>Loading...</div>;

    const handleChange = (key: string, value: any) => {
        setCatalogSettingsEdit((prev: any) => ({
            ...prev,
            [key]: value,
        }));
    };

    // const handleSave = () => {
    //     setSettingsMutation.mutate();
    // };

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>System Settings</h1>
                    </Content>
                </PageSection>
            </PageGroup>
            <PageSection>
                <SettingsTable
                    schema={catalogSchema!}
                    settings={catalogSettingsEdit!}
                />
            </PageSection>
        </Fragment>
    );
};

export default SystemSettingsSection;
