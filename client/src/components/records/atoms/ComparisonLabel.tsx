import { Label, LabelGroup } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import type { Comparison } from "../../../models/api/responses/comparison";
import { useGetSystemInfo } from "../../../hooks/useSystem";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";
import { matchQualityColor } from "../../../models/ui/comparison";

const ComparisonLabel = ({
    recordId,
    comparison: { base, comparator, match_quality, overall_score },
}: {
    recordId: string;
    comparison: Comparison;
}): ReactElement => {
    const { data: systemInfo } = useGetSystemInfo();
    const navigate = useNavigate();

    return (
        <Label
            color={matchQualityColor(match_quality)}
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=comparisons&comparisons.comparator=${comparator}&comparisons.base=${base}`
                )
            }
        >
            {systemInfo?.enabled_comparators.length === 1
                ? `${base}: ${Math.round(overall_score * 100)}%`
                : `${base} ${comparator}: ${Math.round(overall_score * 100)}%`}
        </Label>
    );
};

const ComparisonLabelGroup = ({
    hit: {
        _id,
        _source: { comparisons },
    },
}: {
    hit: EsHit<CatalogRecord>;
}) => {
    if (!comparisons || comparisons.length === 0) return null;

    return (
        <LabelGroup>
            {comparisons.map((comparison, index) => (
                <ComparisonLabel
                    key={index}
                    comparison={comparison}
                    recordId={_id}
                />
            ))}
        </LabelGroup>
    );
};

export { ComparisonLabel, ComparisonLabelGroup };
