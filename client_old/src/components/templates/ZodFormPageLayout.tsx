import { useState, type ReactElement, Fragment, useEffect } from "react";
import {
    Bullseye,
    Content,
    EmptyState,
    PageGroup,
    PageSection,
    Spinner,
} from "@patternfly/react-core";
import type { DefaultValues, FieldValues } from "react-hook-form";
import type { ZodType } from "zod";
import ZodForm from "../organisms/ZodForm";
import { useTranslation } from "react-i18next";

interface ZodFormPageLayoutProps<T extends FieldValues> {
    schema?: ZodType<T, any, any>;
    initValues?: DefaultValues<T>;
    isLoading: boolean;
    onSubmit: (data: T) => void;
    isSubmitting: boolean;
    i18nNamespace: string;
}

const ZodFormPageLayout = <T extends FieldValues>({
    schema,
    initValues,
    isLoading,
    onSubmit,
    isSubmitting,
    i18nNamespace,
}: ZodFormPageLayoutProps<T>): ReactElement => {
    const { t } = useTranslation(i18nNamespace);

    const [dataEdit, setDataEdit] = useState<DefaultValues<T> | undefined>(
        initValues
    );

    useEffect(() => {
        setDataEdit(initValues);
    }, [initValues]);

    if (isLoading) {
        return (
            <Bullseye>
                <Spinner size="xl" />
            </Bullseye>
        );
    }

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>{t("title")}</h1>
                    </Content>
                </PageSection>
            </PageGroup>
            <PageSection>
                {schema ? (
                    <ZodForm
                        schema={schema}
                        defaultValues={dataEdit}
                        onSubmit={onSubmit}
                        isSubmitting={isSubmitting}
                        i18nNamespace={i18nNamespace}
                    />
                ) : (
                    <EmptyState>{t("form.no-data-or-schema")}</EmptyState>
                )}
            </PageSection>
        </Fragment>
    );
};

export default ZodFormPageLayout;
