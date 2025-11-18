import {
    Checkbox,
    Form,
    FormSelect,
    FormSelectOption,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import type { EsHit } from "../../models/api/responses/es";
import type { ReactElement } from "react";

interface ValidationSelectProps {
    record: EsHit<CatalogRecord>;
    validator: string | null;
    showOnlyTarget?: boolean;
    onSubmit: (validator: string, showOnlyTarget: boolean) => void;
}

const ValidationSelect = ({
    record,
    validator,
    showOnlyTarget,
    onSubmit,
}: ValidationSelectProps): ReactElement => {
    return (
        <Form isHorizontal onSubmit={(e) => e.preventDefault()}>
            <Split hasGutter style={{ alignItems: "center" }}>
                <SplitItem>
                    <FormSelect
                        id="validator-name-select"
                        value={validator || ""}
                        onChange={(_, value) =>
                            onSubmit(value, showOnlyTarget ?? false)
                        }
                        placeholder="Select validator name"
                    >
                        <FormSelectOption
                            key="empty"
                            value=""
                            label="Select validator name"
                            isPlaceholder
                        />
                        {record._source.validations?.map((validation, i) => (
                            <FormSelectOption
                                key={i}
                                value={validation.validator}
                                label={validation.validator}
                            />
                        ))}
                    </FormSelect>
                </SplitItem>
                <SplitItem>
                    <Checkbox
                        label="Show only targets"
                        aria-label="Show only targets"
                        id="inlinecheck04"
                        isChecked={showOnlyTarget}
                        onChange={(_, checked) =>
                            onSubmit(validator || "", checked)
                        }
                    />
                </SplitItem>
            </Split>
        </Form>
    );
};
export default ValidationSelect;
