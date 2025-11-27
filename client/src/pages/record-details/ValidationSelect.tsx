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
import { useTranslation } from "react-i18next";

interface ValidationSelectState {
    validator: string;
    showOnlyTarget: boolean;
}

interface ValidationSelectProps {
    record: EsHit<CatalogRecord>;
    state: ValidationSelectState | null;
    onSubmit: (state: ValidationSelectState) => void;
}

const ValidationSelect = ({
    record,
    state,
    onSubmit,
}: ValidationSelectProps): ReactElement => {
    const { t } = useTranslation();

    return (
        <Form isHorizontal onSubmit={(e) => e.preventDefault()}>
            <Split hasGutter style={{ alignItems: "center" }}>
                <SplitItem>
                    <FormSelect
                        id="validator-name-select"
                        value={state?.validator || ""}
                        onChange={(_, value) =>
                            onSubmit({
                                validator: value,
                                showOnlyTarget: state?.showOnlyTarget ?? false,
                            })
                        }
                        placeholder="Select validator name"
                    >
                        {state === null ? (
                            <FormSelectOption
                                key="placeholder"
                                label={t(
                                    "records:details.validations.select-placeholder"
                                )}
                                isPlaceholder
                            />
                        ) : null}
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
                        label={t(
                            "records:details.validations.show-only-targets"
                        )}
                        aria-label="Show only targets"
                        id="inlinecheck04"
                        isChecked={state?.showOnlyTarget ?? false}
                        onChange={(_, checked) =>
                            state &&
                            onSubmit({
                                validator: state.validator,
                                showOnlyTarget: checked,
                            })
                        }
                    />
                </SplitItem>
            </Split>
        </Form>
    );
};
export default ValidationSelect;
