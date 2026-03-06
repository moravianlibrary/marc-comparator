import { Label, LabelGroup } from "@patternfly/react-core";
import {
    orderBy,
    type CatalogRecordState,
} from "../../../models/primitives/catalog_record";
import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";
import {
    CheckIcon,
    TimesIcon,
    TrashIcon,
    EyeIcon,
    EyeSlashIcon,
} from "@patternfly/react-icons";

const STATE_COLOR_MAP: Record<
    CatalogRecordState,
    "teal" | "orangered" | "yellow" | "green" | "grey" | "blue"
> = {
    Active: "teal",
    Deleted: "orangered",
    Unprocessed: "yellow",
    Processed: "green",
    Hidden: "grey",
    Visible: "blue",
};

const STATE_ICON: Record<CatalogRecordState, ReactNode> = {
    Active: <CheckIcon />,
    Deleted: <TrashIcon />,
    Unprocessed: <TimesIcon />,
    Processed: <CheckIcon />,
    Hidden: <EyeSlashIcon />,
    Visible: <EyeIcon />,
};

const RecordStateLabel = ({
    state,
}: {
    state: CatalogRecordState;
}): ReactElement => {
    const { t } = useTranslation();

    return (
        <Label color={STATE_COLOR_MAP[state]} icon={STATE_ICON[state]}>
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
                .sort(orderBy)
                .filter((s) => s !== "Visible")
                .map((state, index) => (
                    <RecordStateLabel key={index} state={state} />
                ))}
        </LabelGroup>
    );
};

export { RecordStateLabel, RecordStateLabelGroup };
