import {
    Card,
    CardBody,
    CardTitle,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    Gallery,
    GalleryItem,
    Label,
    LabelGroup,
    PageSection,
} from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useGetSystemInfo } from "../hooks/useSystem";
import LoadingState from "../components/atoms/LoadingState";
import type { SystemInfo } from "../models/api/responses/system";
import { useSearchCatalogRecords } from "../hooks/useCatalogRecords";
import type { EsTermsAggregation } from "../models/api/responses/es_aggregations";

function formatDuration(sec: number) {
    const d = Math.floor(sec / 86400);
    const h = Math.floor((sec % 86400) / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);

    return `${d}d ${h}h ${m}m ${s}s`;
}

const SystemInfoDescription = ({
    systemInfo,
}: {
    systemInfo: SystemInfo;
}): ReactElement => {
    const renderListField = (values: string[]) => (
        <LabelGroup>
            {values.map((v) => (
                <Label key={v}>{v}</Label>
            ))}
        </LabelGroup>
    );

    return (
        <DescriptionList
            isHorizontal
            isCompact
            horizontalTermWidthModifier={{
                default: "12ch",
                sm: "15ch",
                md: "20ch",
            }}
        >
            <DescriptionListGroup key="system-version">
                <DescriptionListTerm>Version</DescriptionListTerm>
                <DescriptionListDescription>
                    {systemInfo.system_version}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="system-commit">
                <DescriptionListTerm>Commit</DescriptionListTerm>
                <DescriptionListDescription>
                    {systemInfo.system_commit}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="uptime">
                <DescriptionListTerm>Uptime</DescriptionListTerm>
                <DescriptionListDescription>
                    {formatDuration(systemInfo.uptime_seconds)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="available-bases">
                <DescriptionListTerm>Available Bases</DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(systemInfo.available_bases)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-authority-linkers">
                <DescriptionListTerm>
                    Enabled Authority Linkers
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(
                        systemInfo.enabled_authority_linkers.map((a) => a.name)
                    )}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-comparators">
                <DescriptionListTerm>Enabled Comparators</DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(systemInfo.enabled_comparators)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-validators">
                <DescriptionListTerm>Enabled Validators</DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(systemInfo.enabled_validators)}
                </DescriptionListDescription>
            </DescriptionListGroup>
        </DescriptionList>
    );
};

const CatalogRecordsDescription = ({
    stateAggs,
}: {
    stateAggs?: EsTermsAggregation;
}): ReactElement | null => {
    if (!stateAggs) return null;

    return (
        <DescriptionList isHorizontal isCompact>
            <DescriptionListGroup key="total-records">
                <DescriptionListTerm>Total Records</DescriptionListTerm>
                <DescriptionListDescription>
                    {(stateAggs.sum_other_doc_count || 0) +
                        stateAggs.buckets.reduce(
                            (acc, bucket) => acc + bucket.doc_count,
                            0
                        )}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="active-records">
                <DescriptionListTerm>Active Records</DescriptionListTerm>
                <DescriptionListDescription>
                    {
                        stateAggs.buckets.find(
                            (bucket) => bucket.key === "Active"
                        )?.doc_count
                    }
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="deleted-records">
                <DescriptionListTerm>Deleted Records</DescriptionListTerm>
                <DescriptionListDescription>
                    {stateAggs.buckets.find(
                        (bucket) => bucket.key === "Deleted"
                    )?.doc_count || 0}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="hidden-records">
                <DescriptionListTerm>Hidden Records</DescriptionListTerm>
                <DescriptionListDescription>
                    {stateAggs.buckets.find((bucket) => bucket.key === "Hidden")
                        ?.doc_count || 0}
                </DescriptionListDescription>
            </DescriptionListGroup>
        </DescriptionList>
    );
};

const HomePage = (): ReactElement => {
    const { data: systemInfo, isLoading: isLoadingSystemInfo } =
        useGetSystemInfo();
    const { data: catalogRecordAggs, isLoading: isLoadingCatalogRecords } =
        useSearchCatalogRecords({
            query: { match_all: {} },
            aggs: {
                state: {
                    terms: {
                        field: "state",
                    },
                },
            },
        });

    if (isLoadingSystemInfo || isLoadingCatalogRecords) {
        return (
            <PageSection>
                <LoadingState title="" />
            </PageSection>
        );
    }

    console.log(catalogRecordAggs);
    return (
        <PageSection>
            <Gallery
                hasGutter
                minWidths={{ sm: "100%", md: "50%", lg: "40%", xl: "33%" }}
            >
                <GalleryItem>
                    <Card>
                        <CardTitle>System Information</CardTitle>
                        <CardBody>
                            <SystemInfoDescription systemInfo={systemInfo!} />
                        </CardBody>
                    </Card>
                </GalleryItem>
                <GalleryItem>
                    <Card>
                        <CardTitle>Catalog Records Overview</CardTitle>
                        <CardBody>
                            <CatalogRecordsDescription
                                stateAggs={
                                    catalogRecordAggs?.aggregations
                                        ?.state as EsTermsAggregation
                                }
                            />
                        </CardBody>
                    </Card>
                </GalleryItem>
            </Gallery>
        </PageSection>
    );
};

export default HomePage;
