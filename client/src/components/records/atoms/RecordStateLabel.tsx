import { Label, LabelGroup } from "@patternfly/react-core";
import type { CatalogRecordState } from "../../../models/primitives/catalog_record";
import { stateColor, stateOrder } from "../../../models/ui/catalog_record";
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";

const RecordStateLabel = ({
    state,
}: {
    state: CatalogRecordState;
}): ReactElement => {
    const { t } = useTranslation();

    return (
        <Label color={stateColor(state)}>
            {t(`records:types.record-state.${state}`)}
        </Label>
    );
};

const RecordStateLabelGroup = ({
    hit: {
        _source: { state },
    },
}: {
    hit: EsHit<CatalogRecord>;
}) => {
    if (!state) return null;

    return (
        <LabelGroup>
            {state
                .sort(stateOrder)
                .filter((s) => s !== "Visible")
                .map((state, index) => (
                    <RecordStateLabel key={index} state={state} />
                ))}
        </LabelGroup>
    );
};

export { RecordStateLabel, RecordStateLabelGroup };
