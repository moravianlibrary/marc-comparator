import type { ReactElement } from "react";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";
import HitDescription from "../../organisms/HitDescription";
import type { EsHit } from "../../../models/api/responses/es";
import LocalizedDateTime from "../../atoms/LocalizedDateTime";
import MarcTitle from "../../atoms/MarcTitle";
import { useTranslation } from "react-i18next";
import { ComparisonLabelGroup } from "../atoms/ComparisonLabel";
import { AuthorityLinkLabelGroup } from "../atoms/AuthorityLinkLabel";
import { RecordStateLabelGroup } from "../atoms/RecordStateLabel";
import { ValidationLabelGroup } from "../atoms/ValidationLabel";

interface RecordDescriptionProps {
    record: EsHit<CatalogRecord>;
}

const RecordDescription = ({
    record,
}: RecordDescriptionProps): ReactElement => {
    const { t } = useTranslation();

    const config = [
        {
            key: "title",
            label: t("records:fields.title"),
            render: ({ _source: { title, subtitle } }: EsHit<CatalogRecord>) =>
                title ? <MarcTitle title={title} subtitle={subtitle} /> : null,
        },
        { key: "authors", label: t("records:fields.authors") },
        {
            key: "state",
            label: t("records:fields.state"),
            render: (hit: EsHit<CatalogRecord>) => (
                <RecordStateLabelGroup hit={hit} />
            ),
        },
        {
            key: "authority_links",
            label: t("records:fields.authority-links.label"),
            render: (hit: EsHit<CatalogRecord>) => (
                <AuthorityLinkLabelGroup hit={hit} />
            ),
        },
        {
            key: "comparisons",
            label: t("records:fields.comparisons.label"),
            render: (hit: EsHit<CatalogRecord>) => (
                <ComparisonLabelGroup hit={hit} />
            ),
        },
        {
            key: "validations",
            label: t("records:fields.validations.label"),
            render: (hit: EsHit<CatalogRecord>) => (
                <ValidationLabelGroup hit={hit} />
            ),
        },
        {
            key: "latest_sync",
            label: t("records:fields.latest-sync"),
            render: ({ _source: { latest_sync } }: EsHit<CatalogRecord>) =>
                latest_sync ? <LocalizedDateTime date={latest_sync} /> : null,
        },
        {
            key: "latest_transaction",
            label: t("records:fields.latest-transaction"),
            render: ({
                _source: { latest_transaction },
            }: EsHit<CatalogRecord>) =>
                latest_transaction ? (
                    <LocalizedDateTime date={latest_transaction} />
                ) : null,
        },
    ];
    return <HitDescription record={record} config={config} />;
};

export default RecordDescription;
