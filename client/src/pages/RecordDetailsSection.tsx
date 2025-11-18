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
} from "@patternfly/react-core";
import { createRef, Fragment, type ReactElement } from "react";
import { useGetSystemInfo } from "../hooks/useSystem";
import { SearchIcon } from "@patternfly/react-icons";
import { useGetCatalogRecordById } from "../hooks/useCatalogRecords";
import RecordDescription from "./record-details/Description";
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
            base: z.string().nullable().default(null),
        })
        .nullable()
        .default(null),
    comparisons: z
        .object({
            base: z.string().nullable().default(null),
            comparator: z.string().nullable().default(null),
        })
        .nullable()
        .default(null),
    validations: z
        .object({
            validator: z.string().nullable().default(null),
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
    const [params, setParams] = useSearchParamsState(RecordDetailsState);

    const { data: systemInfo, isLoading: systemInfoLoading } =
        useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    const { data: record, isLoading: recordLoading } = useGetCatalogRecordById(
        params.id ?? null
    );

    const descriptionRef = createRef<HTMLDivElement>();
    const marcRef = createRef<HTMLDivElement>();
    const authorityRecordsRef = createRef<HTMLDivElement>();
    const comparisonsRef = createRef<HTMLDivElement>();
    const validationsRef = createRef<HTMLDivElement>();

    const handleTabChange = (newTab: TabKey, tabParams: Object = {}) => {
        setParams({ tab: newTab, id: params.id, ...tabParams });
    };

    const renderAuthorityRecordsTab = (record: EsHit<CatalogRecord>) => (
        <Tab
            eventKey={"authority_records"}
            title={<TabTitleText>Authority Records</TabTitleText>}
            tabContentId={`authority_records-content`}
            tabContentRef={authorityRecordsRef}
        >
            <div style={{ marginTop: "1rem" }}>
                <AuthorityBaseSelect
                    record={record}
                    base={params.authorityLinks?.base ?? null}
                    onSubmit={(base) =>
                        handleTabChange("authority_records", {
                            authorityLinks: { base },
                        })
                    }
                />
            </div>
        </Tab>
    );

    const renderComparisonsTab = (record: EsHit<CatalogRecord>) => (
        <Tab
            eventKey={"comparisons"}
            title={<TabTitleText>Comparisons</TabTitleText>}
            tabContentId={`comparisons-content`}
            tabContentRef={comparisonsRef}
        >
            <div style={{ marginTop: "1rem" }}>
                <ComparisonSelect
                    record={record}
                    base={params.comparisons?.base ?? null}
                    comparator={params.comparisons?.comparator ?? null}
                    onSubmit={(base, comparator) =>
                        handleTabChange("comparisons", {
                            comparisons: { base, comparator },
                        })
                    }
                />
            </div>
        </Tab>
    );

    const renderValidationsTab = (record: EsHit<CatalogRecord>) => (
        <Tab
            eventKey={"validations"}
            title={<TabTitleText>Validations</TabTitleText>}
            tabContentId={`validations-content`}
            tabContentRef={validationsRef}
        >
            <div style={{ marginTop: "1rem" }}>
                <ValidationSelect
                    record={record}
                    validator={params.validations?.validator ?? null}
                    showOnlyTarget={params.validations?.showOnlyTarget}
                    onSubmit={(validator, showOnlyTarget) =>
                        handleTabChange("validations", {
                            validations: { validator, showOnlyTarget },
                        })
                    }
                />
            </div>
        </Tab>
    );

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>Record Details</h1>
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
                                title={<TabTitleText>Description</TabTitleText>}
                                tabContentId="description-content"
                                tabContentRef={descriptionRef}
                            />
                            <Tab
                                eventKey="marc"
                                title={<TabTitleText>MARC Record</TabTitleText>}
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
                            titleText="No Record ID Entered"
                            headingLevel="h4"
                            icon={SearchIcon}
                        >
                            <EmptyStateBody>
                                Please enter a catalog base and system number to
                                view record details.
                            </EmptyStateBody>
                        </EmptyState>
                    </PageSection>
                </PageGroup>
            )}
            {params.id && !record && (
                <PageGroup>
                    <PageSection>
                        <EmptyState
                            titleText="No results found"
                            headingLevel="h4"
                            icon={SearchIcon}
                        >
                            <EmptyStateBody>
                                No record found for the catalog base "
                                {recordIdToBase(params.id)}" and system number "
                                {recordIdToSystemNumber(params.id)}".
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
                                        noDataMessage="No authority records available"
                                    />
                                </TabContent>
                            )}
                        {params.tab === "comparisons" &&
                            record._source.comparisons && (
                                <TabContent
                                    eventKey="comparisons"
                                    id="comparisons-content"
                                    ref={comparisonsRef}
                                ></TabContent>
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
