import { Button, Label, LabelGroup } from "@patternfly/react-core";
import MarcTitle from "../../components/atoms/MarcTitle";
import MonospaceValue from "../../components/atoms/MonospaceValue";
import { type CatalogRecordState } from "../../models/primitives/catalog_record";
import LocalizedDateTime from "../../components/atoms/LocalizedDateTime";
import { DetailsIcon } from "../../components/atoms/Icons";
import { Link } from "react-router";
import { type CatalogRecord } from "../../models/api/responses/catalog_record";
import { type CollectionConfig } from "../../store/collection/domain";

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
            key: "state",
            label: "State",
            alwaysShow: true,
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
                    {hit.authority_links!.map(
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
                    {hit.comparisons!.map(
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
            key: "latest_sync",
            label: "Last Sync",
            visibleByDefault: true,
            render: (hit: Partial<CatalogRecord>) => (
                <LocalizedDateTime date={hit.latest_sync!} />
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
        filter: [],
    };
}
