import {
    Content,
    PageGroup,
    PageSection,
    Spinner,
    EmptyState,
    EmptyStateBody,
    Tabs,
    Tab,
    TabTitleText,
    TabContent,
    Split,
    SplitItem,
    Button,
} from "@patternfly/react-core";
import { createRef, Fragment, type ReactElement } from "react";
import { useGetSystemInfo } from "../hooks/useSystem";
import { RedoIcon, SearchIcon } from "@patternfly/react-icons";
import { useGetCatalogRecordById } from "../hooks/useCatalogRecords";
import RecordDescription from "../components/records/organisms/Description";
import RecordSelect from "./record-details/RecordSelect";
import ComparisonSelect from "./record-details/ComparisonSelect";
import ValidationSelect from "./record-details/ValidationSelect";
import type { EsHit } from "../models/api/responses/es";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import AuthorityBaseSelect from "./record-details/AuthorityBaseSelect";
import MarcRecordTable from "../components/organisms/MarcRecordTable";
import MarcValidationTable from "../components/organisms/MarcValidationTable";
import { z } from "zod";
import { useSearchParamsState } from "../hooks/useSearchParamsState";
import MarcComparisonTable from "../components/organisms/MarcComparisonTable";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";

type TabKey =
    | "description"
    | "marc"
    | "authority_records"
    | "comparisons"
    | "validations";

const RecordDetailsState = z.object({
    tab: z
        .enum([
            "description",
            "marc",
            "authority_records",
            "comparisons",
            "validations",
        ])
        .default("description"),
    id: z.string().nullable().default(null),
    authorityLinks: z
        .object({
            base: z.string(),
        })
        .nullable()
        .default(null),
    comparisons: z
        .object({
            base: z.string(),
            comparator: z.string(),
            showOnlyTarget: z.boolean().default(false),
        })
        .nullable()
        .default(null),
    validations: z
        .object({
            validator: z.string(),
            showOnlyTarget: z.boolean().default(false),
        })
        .nullable()
        .default(null),
});

function recordIdToBase(recordId: string | null): string | null {
    if (!recordId) return null;
    const parts = recordId.split("-");
    return parts.length > 0 ? parts[0] : null;
}

function recordIdToSystemNumber(recordId: string | null): string {
    if (!recordId) return "";
    const parts = recordId.split("-");
    return parts.length > 1 ? parts[1] : "";
}

const RecordDetailsSection = (): ReactElement => {
    const { t } = useTranslation();
    const [params, setParams] = useSearchParamsState(
        RecordDetailsState,
        "record-details"
    );

    const { data: systemInfo, isLoading: systemInfoLoading } =
        useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    const { data: record, isLoading: recordLoading } = useGetCatalogRecordById(
        params.id ?? null
    );
    const queryClient = useQueryClient();

    const handleRefresh = () => {
        queryClient.invalidateQueries({
            queryKey: ["catalog-records", "get-by-id", params.id],
            exact: true,
        });
    };

    const descriptionRef = createRef<HTMLDivElement>();
    const marcRef = createRef<HTMLDivElement>();
    const authorityRecordsRef = createRef<HTMLDivElement>();
    const comparisonsRef = createRef<HTMLDivElement>();
    const validationsRef = createRef<HTMLDivElement>();

    const handleTabChange = (newTab: TabKey, tabParams: Object = {}) => {
        setParams({ tab: newTab, id: params.id, ...tabParams });
    };

    const renderAuthorityRecordsTab = ({
        _source: { authority_links },
    }: EsHit<CatalogRecord>) =>
        authority_links && authority_links.length > 0 ? (
            <Tab
                eventKey={"authority_records"}
                title={
                    <TabTitleText>
                        {t("records:details.views.authority-links")}
                    </TabTitleText>
                }
                tabContentId={`authority_records-content`}
                tabContentRef={authorityRecordsRef}
            >
                <div style={{ marginTop: "1rem" }}>
                    <AuthorityBaseSelect
                        authorityLinks={authority_links}
                        base={params.authorityLinks?.base ?? null}
                        onSubmit={(base) =>
                            handleTabChange("authority_records", {
                                authorityLinks: { base },
                            })
                        }
                    />
                </div>
            </Tab>
        ) : null;

    const renderComparisonsTab = (record: EsHit<CatalogRecord>) =>
        record._source.comparisons && record._source.comparisons.length > 0 ? (
            <Tab
                eventKey={"comparisons"}
                title={
                    <TabTitleText>
                        {t("records:details.views.comparisons")}
                    </TabTitleText>
                }
                tabContentId={`comparisons-content`}
                tabContentRef={comparisonsRef}
            >
                <div style={{ marginTop: "1rem" }}>
                    <ComparisonSelect
                        record={record}
                        state={params.comparisons}
                        onSubmit={(state) =>
                            handleTabChange("comparisons", {
                                comparisons: state,
                            })
                        }
                    />
                </div>
            </Tab>
        ) : null;

    const renderValidationsTab = (record: EsHit<CatalogRecord>) =>
        record._source.validations && record._source.validations.length > 0 ? (
            <Tab
                eventKey={"validations"}
                title={
                    <TabTitleText>
                        {t("records:details.views.validations")}
                    </TabTitleText>
                }
                tabContentId={`validations-content`}
                tabContentRef={validationsRef}
            >
                <div style={{ marginTop: "1rem" }}>
                    <ValidationSelect
                        record={record}
                        state={params.validations}
                        onSubmit={(state) =>
                            handleTabChange("validations", {
                                validations: state,
                            })
                        }
                    />
                </div>
            </Tab>
        ) : null;

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <Split>
                            <SplitItem isFilled>
                                <h1>{t("records:details.title")}</h1>
                            </SplitItem>
                            <SplitItem>
                                <Button
                                    variant="plain"
                                    icon={<RedoIcon />}
                                    onClick={handleRefresh}
                                />
                            </SplitItem>
                        </Split>
                    </Content>
                </PageSection>
                <PageSection>
                    {systemInfoLoading ? (
                        <Spinner size="lg" />
                    ) : (
                        <RecordSelect
                            availableBases={availableBases}
                            base={recordIdToBase(params.id)}
                            systemNumber={recordIdToSystemNumber(params.id)}
                            onSubmit={(base, systemNumber) =>
                                handleTabChange("description", {
                                    id: `${base}-${systemNumber}`,
                                })
                            }
                        />
                    )}
                </PageSection>
                {record && (
                    <PageSection>
                        <Tabs
                            activeKey={params.tab}
                            onSelect={(_e, tabKey) =>
                                handleTabChange(tabKey as TabKey)
                            }
                            role="region"
                        >
                            <Tab
                                eventKey="description"
                                title={
                                    <TabTitleText>
                                        {t("records:details.views.description")}
                                    </TabTitleText>
                                }
                                tabContentId="description-content"
                                tabContentRef={descriptionRef}
                            />
                            <Tab
                                eventKey="marc"
                                title={
                                    <TabTitleText>
                                        {t("records:details.views.marc")}
                                    </TabTitleText>
                                }
                                tabContentId="marc-content"
                                tabContentRef={marcRef}
                            />
                            {renderAuthorityRecordsTab(record)}
                            {renderComparisonsTab(record)}
                            {renderValidationsTab(record)}
                        </Tabs>
                    </PageSection>
                )}
            </PageGroup>
            {recordLoading && (
                <PageGroup>
                    <PageSection>
                        <EmptyState
                            titleText="Loading"
                            headingLevel="h4"
                            icon={Spinner}
                        />
                    </PageSection>
                </PageGroup>
            )}
            {!params.id && (
                <PageGroup>
                    <PageSection>
                        <EmptyState
                            titleText={t(
                                "records:details.statement.no-id-title"
                            )}
                            headingLevel="h4"
                            icon={SearchIcon}
                        >
                            <EmptyStateBody>
                                {t("records:details.statement.no-id-body")}
                            </EmptyStateBody>
                        </EmptyState>
                    </PageSection>
                </PageGroup>
            )}
            {params.id && !record && (
                <PageGroup>
                    <PageSection>
                        <EmptyState
                            titleText={t(
                                "records:details.statement.no-record-found-title"
                            )}
                            headingLevel="h4"
                            icon={SearchIcon}
                        >
                            <EmptyStateBody>
                                {t(
                                    "records:details.statement.no-record-found-body",
                                    {
                                        catalogBase: recordIdToBase(params.id),
                                        systemNumber: recordIdToSystemNumber(
                                            params.id
                                        ),
                                    }
                                )}
                            </EmptyStateBody>
                        </EmptyState>
                    </PageSection>
                </PageGroup>
            )}
            {record && (
                <PageGroup>
                    <PageSection>
                        {params.tab === "description" && (
                            <TabContent
                                eventKey="description"
                                id="description-content"
                                ref={descriptionRef}
                            >
                                <RecordDescription record={record} />
                            </TabContent>
                        )}
                        {params.tab === "marc" && (
                            <TabContent
                                eventKey="marc"
                                id="marc-content"
                                ref={marcRef}
                            >
                                <MarcRecordTable
                                    base={record?._source.base}
                                    systemNumber={record?._source.system_number}
                                />
                            </TabContent>
                        )}
                        {params.tab === "authority_records" &&
                            record._source.authority_links && (
                                <TabContent
                                    eventKey="authority_records"
                                    id="authority_records-content"
                                    ref={authorityRecordsRef}
                                >
                                    <MarcRecordTable
                                        base={
                                            params.authorityLinks?.base ??
                                            undefined
                                        }
                                        systemNumber={
                                            record._source.authority_links.find(
                                                (link) =>
                                                    link.base ===
                                                    params.authorityLinks?.base
                                            )?.system_number
                                        }
                                        noRecordMessage={t(
                                            "records:details.authority-links.no-record-message"
                                        )}
                                    />
                                </TabContent>
                            )}
                        {params.tab === "comparisons" &&
                            record._source.comparisons && (
                                <TabContent
                                    eventKey="comparisons"
                                    id="comparisons-content"
                                    ref={comparisonsRef}
                                >
                                    <MarcComparisonTable
                                        base={record._source.base}
                                        systemNumber={
                                            record._source.system_number
                                        }
                                        comparison={
                                            record._source.comparisons.find(
                                                (comp) =>
                                                    comp.base ===
                                                        params.comparisons
                                                            ?.base &&
                                                    comp.comparator ===
                                                        params.comparisons
                                                            ?.comparator
                                            )!
                                        }
                                        showOnlyTarget={
                                            params.comparisons?.showOnlyTarget
                                        }
                                    />
                                </TabContent>
                            )}
                        {params.tab === "validations" &&
                            record._source.validations && (
                                <TabContent
                                    eventKey="validations"
                                    id="validations-content"
                                    ref={validationsRef}
                                >
                                    <MarcValidationTable
                                        base={record._source.base}
                                        systemNumber={
                                            record._source.system_number
                                        }
                                        validations={(
                                            record._source.validations || []
                                        ).filter(
                                            (validation) =>
                                                params.validations?.validator &&
                                                validation.validator ===
                                                    params.validations
                                                        ?.validator
                                        )}
                                        showOnlyTarget={
                                            params.validations?.showOnlyTarget
                                        }
                                    />
                                </TabContent>
                            )}
                    </PageSection>
                </PageGroup>
            )}
        </Fragment>
    );
};

export default RecordDetailsSection;
