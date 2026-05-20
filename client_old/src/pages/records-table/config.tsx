import MarcTitle from "../../components/atoms/MarcTitle";
import MonospaceValue from "../../components/atoms/MonospaceValue";
import {
    CatalogRecordStateSchema,
    type CatalogRecordState,
} from "../../models/primitives/catalog_record";
import LocalizedDateTime from "../../components/atoms/LocalizedDateTime";
import { type CatalogRecord } from "../../models/api/responses/catalog_record";
import { type CollectionConfig } from "../../store/collection/domain";
import {
    type ValidityStatus,
    ValidityStatusSchema,
} from "../../models/primitives/validation";
import type { TableColumnConfig } from "../../models/ui/hits_table";
import type { EsHit } from "../../models/api/responses/es";
import { stateColor } from "../../models/ui/catalog_record";
import { validityColor } from "../../models/ui/validation";
import { useTranslation } from "react-i18next";
import RecordId from "../../components/records/atoms/RecordId";
import { RecordStateLabelGroup } from "../../components/records/atoms/RecordStateLabel";
import { AuthorityLinkLabelGroup } from "../../components/records/atoms/AuthorityLinkLabel";
import { ComparisonLabelGroup } from "../../components/records/atoms/ComparisonLabel";
import { ValidationLabelGroup } from "../../components/records/atoms/ValidationLabel";

export function generateColumnsConfig(): TableColumnConfig<
    EsHit<CatalogRecord>
>[] {
    const { t } = useTranslation();
    return [
        {
            key: "id",
            label: t("records:fields.id"),
            visibleByDefault: true,
            render: ({ _id }: EsHit<CatalogRecord>) => (
                <RecordId recordId={_id} />
            ),
        },
        {
            key: "base",
            label: t("records:fields.base"),
            render: ({ _source: { base } }: EsHit<CatalogRecord>) =>
                base ? <MonospaceValue value={base} /> : null,
        },
        {
            key: "system_number",
            label: t("records:fields.system-number"),
            render: ({ _source: { system_number } }: EsHit<CatalogRecord>) =>
                system_number ? <MonospaceValue value={system_number} /> : null,
        },
        {
            key: "title",
            label: t("records:fields.title"),
            render: ({ _source: { title, subtitle } }: EsHit<CatalogRecord>) =>
                title ? <MarcTitle title={title} subtitle={subtitle} /> : null,
        },
        {
            key: "authors",
            label: t("records:fields.authors"),
        },
        {
            key: "state",
            label: t("records:fields.state"),
            visibleByDefault: true,
            render: (hit: EsHit<CatalogRecord>) => (
                <RecordStateLabelGroup hit={hit} />
            ),
        },
        {
            key: "authority_links",
            label: t("records:fields.authority-links.label"),
            visibleByDefault: true,
            render: (hit: EsHit<CatalogRecord>) => (
                <AuthorityLinkLabelGroup hit={hit} />
            ),
        },
        {
            key: "comparisons",
            label: t("records:fields.comparisons.label"),
            visibleByDefault: true,
            render: (hit: EsHit<CatalogRecord>) => (
                <ComparisonLabelGroup hit={hit} />
            ),
        },
        {
            key: "validations",
            label: t("records:fields.validations.label"),
            visibleByDefault: true,
            render: (hit: EsHit<CatalogRecord>) => (
                <ValidationLabelGroup hit={hit} />
            ),
        },
        {
            key: "latest_sync",
            label: t("records:fields.latest-sync"),
            visibleByDefault: true,
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
}

export function generateCatalogRecordsConfig<T>(): CollectionConfig<T> {
    return {
        columns: generateColumnsConfig(),
        perPage: { options: [10, 20, 50, 100], default: 10 },
        search: { fields: [] },
        filter: [
            {
                type: "term",
                field: "state",
                sizeOptions: [10],
                labelProps: (bucketKey: string) => ({
                    color: stateColor(bucketKey as CatalogRecordState),
                }),
                labelI18nKey: (bucketKey: string) =>
                    `records:types.record-state.${bucketKey}`,
                displayOrder: CatalogRecordStateSchema.options,
            },
            {
                type: "term",
                field: "authority_links.base",
                sizeOptions: [10, 20, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "comparisons.base",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "comparisons.comparator",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "comparisons.status",
                sizeOptions: [4],
                isNested: true,
            },
            {
                type: "histogram",
                field: "comparisons.overall_score",
                interval: 1,
                min: 0,
                max: 100,
                isNested: true,
            },
            {
                type: "term",
                field: "comparisons.field_results.explanation",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "comparisons.field_results.subfield_results.explanation",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "validations.validator",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "validations.status",
                sizeOptions: [4],
                labelProps: (bucketKey: string) => ({
                    color: validityColor(bucketKey as ValidityStatus),
                }),
                labelI18nKey: (bucketKey: string) =>
                    `records:types.validity-status.${bucketKey}`,
                displayOrder: ValidityStatusSchema.options,
                isNested: true,
            },
            {
                type: "term",
                field: "validations.target.tag",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "validations.target.codes",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "validations.reason",
                sizeOptions: [10, 50],
                isNested: true,
            },
            {
                type: "term",
                field: "type_of_record",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "bibliographic_level",
                sizeOptions: [10, 50],
            },
            {
                type: "date-range",
                field: "latest_sync",
            },
            {
                type: "date-range",
                field: "latest_transaction",
            },
        ],
    };
}
