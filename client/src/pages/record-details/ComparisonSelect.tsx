import { type ReactElement } from "react";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import type { EsHit } from "../../models/api/responses/es";
import {
    Checkbox,
    Form,
    FormSelect,
    FormSelectOption,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import { useTranslation } from "react-i18next";

interface ComparisonSelectState {
    base: string;
    comparator: string;
    showOnlyTarget: boolean;
}

interface ComparisonSelectProps {
    record: EsHit<CatalogRecord>;
    state: ComparisonSelectState | null;
    onSubmit: (state: ComparisonSelectState) => void;
}

const ComparisonSelect = ({
    record,
    state,
    onSubmit,
}: ComparisonSelectProps): ReactElement => {
    const { t } = useTranslation();

    const handleSubmitComparison = (value: string) => {
        const values = value.split(" - ");
        if (values.length !== 2) return;

        onSubmit({
            base: values[0],
            comparator: values[1],
            showOnlyTarget: state?.showOnlyTarget || false,
        });
    };

    const handleSubmitShowOnlyTarget = (showOnlyTarget: boolean) => {
        if (state === null) return;
        onSubmit({
            base: state.base,
            comparator: state.comparator,
            showOnlyTarget,
        });
    };

    return (
        <Form isHorizontal onSubmit={(e) => e.preventDefault()}>
            <Split hasGutter style={{ alignItems: "center" }}>
                <SplitItem>
                    <FormSelect
                        id="comparison-base-select"
                        value={
                            state ? `${state.base} - ${state.comparator}` : ""
                        }
                        onChange={(_, value) =>
                            value && handleSubmitComparison(value)
                        }
                    >
                        {state === null ? (
                            <FormSelectOption
                                key="placeholder"
                                label={t(
                                    "records:details.comparisons.select-placeholder"
                                )}
                                isPlaceholder
                            />
                        ) : null}
                        {record._source.comparisons
                            ?.map(
                                ({ comparator, base }) =>
                                    `${base} - ${comparator}`
                            )
                            .map((comparison, i) => (
                                <FormSelectOption
                                    key={i}
                                    value={comparison}
                                    label={comparison}
                                />
                            ))}
                    </FormSelect>
                </SplitItem>
                <SplitItem>
                    <Checkbox
                        label={t(
                            "records:details.comparisons.show-only-targets"
                        )}
                        aria-label="Show only targets"
                        id="inlinecheck04"
                        isChecked={state?.showOnlyTarget || false}
                        onChange={(_, checked) =>
                            handleSubmitShowOnlyTarget(checked)
                        }
                    />
                </SplitItem>
            </Split>
        </Form>
    );
};

export default ComparisonSelect;
