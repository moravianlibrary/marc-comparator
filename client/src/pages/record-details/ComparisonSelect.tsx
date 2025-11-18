import { useEffect, useState, type ReactElement } from "react";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import type { EsHit } from "../../models/api/responses/es";
import {
    Form,
    FormSelect,
    FormSelectOption,
    Split,
    SplitItem,
} from "@patternfly/react-core";

interface ComparisonSelectProps {
    record: EsHit<CatalogRecord>;
    base: string | null;
    comparator: string | null;
    onSubmit: (base: string, comparator: string) => void;
}

const ComparisonSelect = ({
    record,
    base,
    comparator,
    onSubmit,
}: ComparisonSelectProps): ReactElement => {
    const [baseState, setBaseState] = useState(base || "");
    const [comparatorState, setComparatorState] = useState(comparator || "");

    useEffect(() => {
        setBaseState(base || "");
    }, [base]);

    useEffect(() => {
        setComparatorState(comparator || "");
    }, [comparator]);

    const handleValueChange = (newBase: string, newName: string) => {
        setBaseState(newBase);
        setComparatorState(newName);

        if (newBase && newName) {
            onSubmit(newBase, newName);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        handleValueChange(baseState, comparatorState);
    };

    return (
        <Form isHorizontal onSubmit={handleSubmit}>
            <Split hasGutter>
                <SplitItem>
                    <FormSelect
                        id="comparison-base-select"
                        value={baseState}
                        onChange={(_, value) =>
                            handleValueChange(value, comparatorState)
                        }
                    >
                        <FormSelectOption
                            key="empty"
                            value=""
                            label="Select comparison base"
                            isPlaceholder
                        />
                        {record._source.comparisons
                            ?.filter(
                                (item, index, arr) =>
                                    arr.findIndex(
                                        (x) => x.base === item.base
                                    ) === index
                            )
                            .map((comparison, i) => (
                                <FormSelectOption
                                    key={i}
                                    value={comparison.base}
                                    label={comparison.base}
                                />
                            ))}
                    </FormSelect>
                </SplitItem>
                <SplitItem>
                    <FormSelect
                        id="comparator-name-select"
                        value={comparatorState}
                        onChange={(_, value) =>
                            handleValueChange(baseState, value)
                        }
                    >
                        <FormSelectOption
                            key="empty"
                            value=""
                            label="Select comparator name"
                            isPlaceholder
                        />
                        {record._source.comparisons?.map((comparison, i) => (
                            <FormSelectOption
                                key={i}
                                value={comparison.comparator}
                                label={comparison.comparator}
                            />
                        ))}
                    </FormSelect>
                </SplitItem>
            </Split>
        </Form>
    );
};

export default ComparisonSelect;
