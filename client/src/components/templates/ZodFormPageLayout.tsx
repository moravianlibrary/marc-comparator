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

interface ZodFormPageLayoutProps<T extends FieldValues> {
    schema?: ZodType<T, any, any>;
    initValues?: DefaultValues<T>;
    isLoading: boolean;
    onSubmit: (data: T) => void;
    isSubmitting: boolean;
    title: string;
    emptyStateMessage?: string;
}

const ZodFormPageLayout = <T extends FieldValues>({
    schema,
    initValues,
    isLoading,
    onSubmit,
    isSubmitting,
    title,
    emptyStateMessage = "No data or schema available.",
}: ZodFormPageLayoutProps<T>): ReactElement => {
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
                        <h1>{title}</h1>
                    </Content>
                </PageSection>
            </PageGroup>
            <PageSection>
                {schema && dataEdit ? (
                    <ZodForm
                        schema={schema}
                        defaultValues={dataEdit}
                        onSubmit={onSubmit}
                        isSubmitting={isSubmitting}
                    />
                ) : (
                    <EmptyState>{emptyStateMessage}</EmptyState>
                )}
            </PageSection>
        </Fragment>
    );
};

export default ZodFormPageLayout;
