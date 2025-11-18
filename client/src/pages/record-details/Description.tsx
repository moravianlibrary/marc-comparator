import type { ReactElement } from "react";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import HitDescription from "../../components/organisms/HitDescription";
import type { EsHit } from "../../models/api/responses/es";
import LocalizedDateTime from "../../components/atoms/LocalizedDateTime";
import { Label, LabelGroup } from "@patternfly/react-core";
import { stateColor, stateOrder } from "../../models/ui/catalog_record";
import type { CatalogRecordState } from "../../models/primitives/catalog_record";
import MarcTitle from "../../components/atoms/MarcTitle";
import AuthorityLinkLabel from "../../components/atoms/AuthorityLinkLabel";
import ComparisonLabel from "../../components/atoms/ComparisonLabel";
import ValidationLabel from "../../components/atoms/ValidationLabel";

interface RecordDescriptionProps {
    record: EsHit<CatalogRecord>;
}

const RecordDescription = ({
    record,
}: RecordDescriptionProps): ReactElement => {
    const config = [
        {
            key: "title",
            label: "Title",
            render: ({
                _source: { title, subtitle },
            }: EsHit<CatalogRecord>) => (
                <MarcTitle title={title || "N/A"} subtitle={subtitle} />
            ),
        },
        {
            key: "authors",
            label: "Authors",
        },
        {
            key: "state",
            label: "State",
            render: ({ _source: { state } }: EsHit<CatalogRecord>) => (
                <LabelGroup>
                    {(state || [])
                        .sort(stateOrder)
                        .map((state: CatalogRecordState, index: number) => (
                            <Label key={index} color={stateColor(state)}>
                                {state}
                            </Label>
                        ))}
                </LabelGroup>
            ),
        },
        {
            key: "authority_links",
            label: "Authority Links",
            render: ({
                _id,
                _source: { authority_links },
            }: EsHit<CatalogRecord>) => (
                <LabelGroup>
                    {(authority_links || []).map((link, index) => (
                        <AuthorityLinkLabel
                            key={index}
                            recordId={_id}
                            authorityLink={link}
                        />
                    ))}
                </LabelGroup>
            ),
        },
        {
            key: "comparisons",
            label: "Comparisons",
            render: ({
                _id,
                _source: { comparisons },
            }: EsHit<CatalogRecord>) => (
                <LabelGroup>
                    {(comparisons || []).map((comparison, index) => (
                        <ComparisonLabel
                            key={index}
                            recordId={_id}
                            comparison={comparison}
                        />
                    ))}
                </LabelGroup>
            ),
        },
        {
            key: "validations",
            label: "Validations",
            render: ({
                _id,
                _source: { validations },
            }: EsHit<CatalogRecord>) => (
                <LabelGroup>
                    {(validations || []).map((validation, index) => (
                        <ValidationLabel
                            key={index}
                            recordId={_id}
                            validation={validation}
                        />
                    ))}
                </LabelGroup>
            ),
        },
        {
            key: "latest_sync",
            label: "Last Sync",
            render: ({ _source: { latest_sync } }: EsHit<CatalogRecord>) =>
                latest_sync && <LocalizedDateTime date={latest_sync} />,
        },
        {
            key: "latest_transaction",
            label: "Last Transaction",
            render: ({
                _source: { latest_transaction },
            }: EsHit<CatalogRecord>) =>
                latest_transaction && (
                    <LocalizedDateTime date={latest_transaction} />
                ),
        },
    ];
    return <HitDescription record={record} config={config} />;
};

export default RecordDescription;
