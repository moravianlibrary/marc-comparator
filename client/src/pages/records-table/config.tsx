import { Button, Label, LabelGroup } from "@patternfly/react-core";
import MarcTitle from "../../components/atoms/MarcTitle";
import MonospaceValue from "../../components/atoms/MonospaceValue";
import {
    CatalogRecordStateSchema,
    type CatalogRecordState,
} from "../../models/primitives/catalog_record";
import LocalizedDateTime from "../../components/atoms/LocalizedDateTime";
import { DetailsIcon } from "../../components/atoms/Icons";
import { Link } from "react-router";
import { type CatalogRecord } from "../../models/api/responses/catalog_record";
import { type CollectionConfig } from "../../store/collection/domain";
import {
    type ValidityStatus,
    ValidityStatusSchema,
} from "../../models/primitives/validation";
import type { TableColumnConfig } from "../../models/ui/hits_table";
import type { EsHit } from "../../models/api/responses/es";
import { stateColor, stateOrder } from "../../models/ui/catalog_record";
import { validityColor } from "../../models/ui/validation";
import AuthorityLinkLabel from "../../components/atoms/AuthorityLinkLabel";
import ComparisonLabel from "../../components/atoms/ComparisonLabel";
import ValidationLabel from "../../components/atoms/ValidationLabel";

export function generateColumnsConfig(): TableColumnConfig<
    EsHit<CatalogRecord>
>[] {
    return [
        {
            key: "id",
            label: "ID",
            visibleByDefault: true,
            render: ({ _id }: EsHit<CatalogRecord>) => (
                <MonospaceValue value={_id} />
            ),
        },
        {
            key: "base",
            label: "Base",
            render: ({ _source: { base } }: EsHit<CatalogRecord>) =>
                base ? <MonospaceValue value={base} /> : undefined,
        },
        {
            key: "system_number",
            label: "System Number",
            render: ({ _source: { system_number } }: EsHit<CatalogRecord>) =>
                system_number ? (
                    <MonospaceValue value={system_number} />
                ) : undefined,
        },
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
            visibleByDefault: true,
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
            visibleByDefault: true,
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
            visibleByDefault: true,
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
            visibleByDefault: true,
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
            visibleByDefault: true,
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
        {
            key: "details",
            label: "Details",
            render: ({ _id }: EsHit<CatalogRecord>) => (
                <Link to={`/records/details?id=${_id}`}>
                    <Button variant="plain" icon={<DetailsIcon />} />
                </Link>
            ),
            alwaysShow: true,
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
                displayOrder: CatalogRecordStateSchema.options,
            },
            {
                type: "term",
                field: "authority_links.base",
                sizeOptions: [10, 20, 50],
            },
            {
                type: "term",
                field: "comparisons.base",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "comparisons.comparator",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "comparisons.status",
                sizeOptions: [4],
            },
            {
                type: "histogram",
                field: "comparisons.overall_score",
                interval: 1,
                min: 0,
                max: 100,
            },
            {
                type: "term",
                field: "comparisons.field_results.explanation",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "comparisons.field_results.subfield_results.explanation",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "validations.validator",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "validations.status",
                sizeOptions: [4],
                labelProps: (bucketKey: string) => ({
                    color: validityColor(bucketKey as ValidityStatus),
                }),
                displayOrder: ValidityStatusSchema.options,
            },
            {
                type: "term",
                field: "validations.target.tag",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "validations.target.codes",
                sizeOptions: [10, 50],
            },
            {
                type: "term",
                field: "validations.reason",
                sizeOptions: [10, 50],
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
