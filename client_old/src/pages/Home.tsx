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
import { useTranslation } from "react-i18next";

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
    const { t } = useTranslation();
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
                sm: "20ch",
                md: "25ch",
            }}
        >
            <DescriptionListGroup key="system-version">
                <DescriptionListTerm>
                    {t("home:system-info.system-version")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {systemInfo.system_version}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="system-commit">
                <DescriptionListTerm>
                    {t("home:system-info.system-commit")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {systemInfo.system_commit}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="uptime">
                <DescriptionListTerm>
                    {t("home:system-info.system-uptime")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {formatDuration(systemInfo.uptime_seconds)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="available-bases">
                <DescriptionListTerm>
                    {t("home:system-info.available-bases")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(systemInfo.available_bases)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-authority-linkers">
                <DescriptionListTerm>
                    {t("home:system-info.enabled-authority-linkers")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(
                        systemInfo.enabled_authority_linkers.map((a) => a.name)
                    )}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-comparators">
                <DescriptionListTerm>
                    {t("home:system-info.enabled-comparators")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {renderListField(systemInfo.enabled_comparators)}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="enabled-validators">
                <DescriptionListTerm>
                    {t("home:system-info.enabled-validators")}
                </DescriptionListTerm>
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
    const { t } = useTranslation();

    if (!stateAggs) return null;

    return (
        <DescriptionList
            isHorizontal
            isCompact
            horizontalTermWidthModifier={{
                sm: "16ch",
                md: "20ch",
            }}
        >
            <DescriptionListGroup key="total-records">
                <DescriptionListTerm>
                    {t("home:catalog-records-overview.total-records")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {(stateAggs.sum_other_doc_count || 0) +
                        stateAggs.buckets.reduce(
                            (acc, bucket) =>
                                ["Active", "Deleted"].includes(
                                    bucket.key.toString()
                                )
                                    ? acc + bucket.doc_count
                                    : acc,
                            0
                        )}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="active-records">
                <DescriptionListTerm>
                    {t("home:catalog-records-overview.active-records")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {
                        stateAggs.buckets.find(
                            (bucket) => bucket.key === "Active"
                        )?.doc_count
                    }
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="deleted-records">
                <DescriptionListTerm>
                    {t("home:catalog-records-overview.deleted-records")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {stateAggs.buckets.find(
                        (bucket) => bucket.key === "Deleted"
                    )?.doc_count || 0}
                </DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup key="hidden-records">
                <DescriptionListTerm>
                    {t("home:catalog-records-overview.hidden-records")}
                </DescriptionListTerm>
                <DescriptionListDescription>
                    {stateAggs.buckets.find((bucket) => bucket.key === "Hidden")
                        ?.doc_count || 0}
                </DescriptionListDescription>
            </DescriptionListGroup>
        </DescriptionList>
    );
};

const HomePage = (): ReactElement => {
    const { t } = useTranslation();
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

    return (
        <PageSection>
            <Gallery
                hasGutter
                minWidths={{ sm: "100%", md: "50%", lg: "40%", xl: "33%" }}
            >
                <GalleryItem>
                    <Card>
                        <CardTitle>{t("home:system-info.title")}</CardTitle>
                        <CardBody>
                            <SystemInfoDescription systemInfo={systemInfo!} />
                        </CardBody>
                    </Card>
                </GalleryItem>
                <GalleryItem>
                    <Card>
                        <CardTitle>
                            {t("home:catalog-records-overview.title")}
                        </CardTitle>
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
