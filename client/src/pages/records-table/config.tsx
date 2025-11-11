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

const STATE_RANKING: Record<CatalogRecordState, number> = {
    Active: 1,
    Deleted: 2,
    Valid: 3,
    Invalid: 4,
    Hidden: 5,
};

const STATE_COLOR_MAP: Record<
    CatalogRecordState,
    "yellow" | "grey" | "green" | "red" | "blue"
> = {
    Active: "yellow",
    Deleted: "grey",
    Valid: "green",
    Invalid: "red",
    Hidden: "blue",
};

const VALIDITY_STATUS_MAP: Record<
    ValidityStatus,
    "success" | "danger" | "warning" | "info"
> = {
    Valid: "success",
    Invalid: "danger",
    Warning: "warning",
    Info: "info",
};

function generateColumnsConfig() {
    return [
        {
            key: "id",
            label: "ID",
            visibleByDefault: true,
            render: (hit: Partial<CatalogRecord>) => (
                <MonospaceValue value={`${hit.base}-${hit.system_number}`} />
            ),
        },
        {
            key: "base",
            label: "Base",
            render: (hit: Partial<CatalogRecord>) => (
                <MonospaceValue value={hit.base!} />
            ),
        },
        {
            key: "system_number",
            label: "System Number",
            render: (hit: Partial<CatalogRecord>) => (
                <MonospaceValue value={hit.system_number!} />
            ),
        },
        {
            key: "title",
            label: "Title",
            render: (hit: Partial<CatalogRecord>) => (
                <MarcTitle title={hit.title!} subtitle={hit.subtitle} />
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
            render: (hit: Partial<CatalogRecord>) => (
                <LabelGroup>
                    {hit
                        .state!.sort(
                            (a, b) => STATE_RANKING[a] - STATE_RANKING[b]
                        )
                        .map((state: CatalogRecordState, index: number) => (
                            <Label key={index} color={STATE_COLOR_MAP[state]}>
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
            render: (hit: Partial<CatalogRecord>) => (
                <LabelGroup>
                    {(hit.authority_links || []).map(
                        (link: { base: string }, index: number) => (
                            <Label key={index}>{link.base}</Label>
                        )
                    )}
                </LabelGroup>
            ),
        },
        {
            key: "comparisons",
            label: "Comparisons",
            visibleByDefault: true,
            render: (hit: Partial<CatalogRecord>) => (
                <LabelGroup>
                    {(hit.comparisons || []).map(
                        (
                            c: {
                                base: string;
                                comparator: string;
                                overall_score: number;
                            },
                            index: number
                        ) => (
                            <Label key={index}>
                                {c.base} {c.comparator}: {c.overall_score}
                            </Label>
                        )
                    )}
                </LabelGroup>
            ),
        },
        {
            key: "validations",
            label: "Validations",
            visibleByDefault: true,
            render: (hit: Partial<CatalogRecord>) => (
                <LabelGroup>
                    {(hit.validations || []).map(
                        (
                            v: {
                                validator: string;
                                status: string;
                            },
                            index: number
                        ) => (
                            <Label
                                key={index}
                                status={
                                    VALIDITY_STATUS_MAP[
                                        v.status as ValidityStatus
                                    ]
                                }
                            >
                                {v.validator}
                            </Label>
                        )
                    )}
                </LabelGroup>
            ),
        },
        {
            key: "latest_sync",
            label: "Last Sync",
            visibleByDefault: true,
            render: (hit: Partial<CatalogRecord>) =>
                hit.latest_sync && <LocalizedDateTime date={hit.latest_sync} />,
        },
        {
            key: "latest_transaction",
            label: "Last Transaction",
            render: (hit: Partial<CatalogRecord>) =>
                hit.latest_transaction && (
                    <LocalizedDateTime date={hit.latest_transaction} />
                ),
        },
        {
            key: "details",
            label: "Details",
            render: (hit: Partial<CatalogRecord>) => (
                <Link
                    to={`/records/details?id=${hit.base}-${hit.system_number}`}
                >
                    <Button variant="plain" icon={<DetailsIcon />} />
                </Link>
            ),
            alwaysShow: true,
        },
    ];
}

export function generateCatalogRecordsConfig(): CollectionConfig {
    return {
        columns: generateColumnsConfig(),
        perPage: { options: [10, 20, 50, 100], default: 10 },
        search: { fields: [] },
        filter: [
            {
                type: "terms",
                field: "state",
                sizeOptions: [10],
                labelProps: (bucketKey: string) => ({
                    color: STATE_COLOR_MAP[bucketKey as CatalogRecordState],
                }),
                displayOrder: CatalogRecordStateSchema.options,
            },
            {
                type: "terms",
                field: "authority_links.base",
                sizeOptions: [10, 20, 50],
            },
            {
                type: "terms",
                field: "comparisons.base",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "comparisons.comparator",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
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
                type: "terms",
                field: "comparisons.field_results.explanation",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "comparisons.field_results.subfield_results.explanation",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "validations.validator",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "validations.status",
                sizeOptions: [4],
                labelProps: (bucketKey: string) => ({
                    status: VALIDITY_STATUS_MAP[bucketKey as ValidityStatus],
                }),
                displayOrder: ValidityStatusSchema.options,
            },
            {
                type: "terms",
                field: "validations.target.tag",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "validations.target.codes",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "validations.reason",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
                field: "type_of_record",
                sizeOptions: [10, 50],
            },
            {
                type: "terms",
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
