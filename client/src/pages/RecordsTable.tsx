import { Fragment, useMemo, useRef, useState, type ReactElement } from "react";
import { useSearchCatalogRecordsBatch } from "../hooks/useCatalogRecords";
import {
    InnerScrollContainer,
    OuterScrollContainer,
} from "@patternfly/react-table";
import RecordsTableToolbar from "./records-table/Toolbar";
import HitsTable from "../components/organisms/HitsTable";
import {
    ActionList,
    ActionListGroup,
    ActionListItem,
    Button,
    PageGroup,
    PageSection,
    Pagination,
    Stack,
    StackItem,
} from "@patternfly/react-core";
import { type CollectionData } from "../store/collection/domain";
import { buildRequests } from "../store/es/requests_factory";
import { buildCollectionData } from "../store/collection/data_factory";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { useTranslation } from "react-i18next";
import { useSearchParamsState } from "../hooks/useSearchParamsState";
import { esStateReducer } from "../store/es/reducer";
import { EsStateSchema } from "../store/es/domain";
import RecordId from "../components/records/atoms/RecordId";
import MonospaceValue from "../components/atoms/MonospaceValue";
import MarcTitle from "../components/atoms/MarcTitle";
import {
    RecordStateLabel,
    RecordStateLabelGroup,
} from "../components/records/atoms/RecordStateLabel";
import { AuthorityLinkLabelGroup } from "../components/records/atoms/AuthorityLinkLabel";
import LocalizedDateTime from "../components/atoms/LocalizedDateTime";
import { ComparisonLabelGroup } from "../components/records/atoms/ComparisonLabel";
import { ValidationLabelGroup } from "../components/records/atoms/ValidationLabel";
import EsTermsLabelGroup from "../components/molecules/EsTermsLabelGroup";
import EsHistogram from "../components/molecules/EsHistogram";
import type { CatalogRecordState } from "../models/primitives/catalog_record";
import { MatchQualitySchema } from "../models/primitives/comparison";

const RecordsTable = (): ReactElement => {
    const { t } = useTranslation("records");
    const { t: t_comparators } = useTranslation("comparators-config");

    const { state, dispatch } = useSearchParamsState(EsStateSchema, {
        storeKey: "esRecordsTableState",
        defaultValues: {
            config: {
                columnFields: {
                    id: [],
                    title: ["title", "subtitle"],
                },
                search: {
                    fields: [
                        "system_number",
                        "title",
                        "subtitle",
                        "authors",
                        "authority_links.system_number",
                    ],
                },
                sortBy: {
                    relevance: [{ _score: { order: "desc" } }],
                    "latest-sync-desc": [{ latest_sync: { order: "desc" } }],
                    "latest-sync-asc": [{ latest_sync: { order: "asc" } }],
                    "latest-transaction-desc": [
                        { latest_transaction: { order: "desc" } },
                    ],
                    "latest-transaction-asc": [
                        { latest_transaction: { order: "asc" } },
                    ],
                    "title-asc": [{ "title.keyword": { order: "asc" } }],
                    "title-desc": [{ "title.keyword": { order: "desc" } }],
                    "score-intiim-desc": [
                        {
                            "comparisons.overall_score": {
                                order: "desc",
                                mode: "max",
                                nested: {
                                    path: "comparisons",
                                    filter: {
                                        term: {
                                            "comparisons.comparator": "intiim",
                                        },
                                    },
                                },
                            },
                        },
                    ],
                    "score-intiim-asc": [
                        {
                            "comparisons.overall_score": {
                                order: "asc",
                                mode: "max",
                                nested: {
                                    path: "comparisons",
                                    filter: {
                                        term: {
                                            "comparisons.comparator": "intiim",
                                        },
                                    },
                                },
                            },
                        },
                    ],
                },
                filters: {
                    state: { type: "terms", size: 4 },
                    "authority_links.base": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "comparisons.base": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "comparisons.comparator": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "comparisons.match_quality": {
                        type: "terms",
                        size: 3,
                        nested: true,
                    },
                    "comparisons.overall_score": {
                        type: "histogram",
                        interval: 0.01,
                        min: 0.0,
                        max: 1.0,
                        coef: 100,
                        nested: true,
                    },
                    "comparisons.field_results.explanation": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "comparisons.field_results.subfield_results.explanation": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "validations.validator": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "validations.status": {
                        type: "terms",
                        size: 4,
                        nested: true,
                    },
                    "validations.target.tag": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "validations.target.codes": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    "validations.reason": {
                        type: "terms",
                        size: 10,
                        nested: true,
                    },
                    type_of_record: { type: "terms", size: 10 },
                    bibliographic_level: { type: "terms", size: 10 },
                },
                perPage: { options: [10, 25, 50, 100], default: 10 },
            },
            columns: {
                id: { order: 0, visible: true },
                base: { order: 1, visible: false },
                system_number: { order: 2, visible: false },
                title: { order: 3, visible: false },
                authors: { order: 4, visible: false },
                state: { order: 5, visible: true },
                authority_links: { order: 6, visible: true },
                comparisons: { order: 7, visible: true },
                validations: { order: 8, visible: true },
                latest_sync: { order: 9, visible: true },
                latest_transaction: { order: 10, visible: false },
            },
            sortBy: "relevance",
        },
        softDefaultValues: {
            terms: {
                state: { include: ["Visible"] },
            },
        },
        reducer: esStateReducer,
    });

    const requests = useMemo(
        () => buildRequests(state),
        [
            state.page,
            state.perPage,
            state.searchTerm,
            state.searchFuzziness,
            JSON.stringify(state.terms),
            JSON.stringify(state.hist),
            state.sortBy,
            JSON.stringify(state.columns),
        ]
    );

    const queryResponses = useSearchCatalogRecordsBatch(requests || []);

    const prevDataRef = useRef<CollectionData<CatalogRecord>>({
        isLoading: true,
        isError: false,
        error: null,
        hits: [],
        totalItems: 0,
        aggregations: {},
    });
    const data: CollectionData<CatalogRecord> = useMemo(() => {
        if (!queryResponses || queryResponses.length === 0) {
            return prevDataRef.current;
        }

        const newData = buildCollectionData<CatalogRecord>(
            queryResponses,
            prevDataRef.current
        );

        prevDataRef.current = newData;

        return newData;
    }, [queryResponses]);

    const { isLoading, isError, error, hits, totalItems } = data;

    const [showFilters, setShowFilters] = useState<boolean>(false);

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        dispatch({
            type: "setPaginationParams",
            page: newPage,
            perPage: newPerPage || state.perPage || 0,
        });
    };

    const handleClearFilters = () => {
        dispatch({ type: "clearFilters" });
    };

    const toolbar = (
        <RecordsTableToolbar
            state={state}
            dispatch={dispatch}
            data={data}
            showFilters={showFilters}
            onToggleShowFilters={() => setShowFilters(!showFilters)}
        />
    );

    if (showFilters) {
        return (
            <Fragment>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>{toolbar}</PageSection>
                </PageGroup>
                <PageGroup>
                    <PageSection>
                        <Stack>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="state"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    renderBucketLabel={({ key }) => (
                                        <RecordStateLabel
                                            state={key as CatalogRecordState}
                                        />
                                    )}
                                    title={t("fields.state")}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="authority_links.base"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.authority-links-object.base"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="comparisons.base"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t("fields.comparisons-object.base")}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="comparisons.comparator"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    renderBucketLabel={({ key }) =>
                                        t_comparators(`${key}.title`)
                                    }
                                    title={t(
                                        "fields.comparisons-object.comparator"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="comparisons.match_quality"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    bucketsOrder={MatchQualitySchema.options}
                                    title={t(
                                        "fields.comparisons-object.match-quality"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsHistogram
                                    field="comparisons.overall_score"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.comparisons-object.overall-score"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="comparisons.field_results.explanation"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.comparisons-object.field-results.explanation"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="comparisons.field_results.subfield_results.explanation"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.comparisons-object.field-results.subfield-results.explanation"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="validations.validator"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.validations-object.validator"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="validations.status"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.validations-object.status"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="validations.target.tag"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.validations-object.target.tag"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="validations.target.codes"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.validations-object.target.codes"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="validations.reason"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t(
                                        "fields.validations-object.reason"
                                    )}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="type_of_record"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t("fields.type-of-record")}
                                />
                            </StackItem>
                            <StackItem>
                                <EsTermsLabelGroup
                                    field="bibliographic_level"
                                    data={data}
                                    state={state}
                                    dispatch={dispatch}
                                    title={t("fields.bibliographic-level")}
                                />
                            </StackItem>
                        </Stack>
                    </PageSection>
                </PageGroup>
                <PageGroup stickyOnBreakpoint={{ default: "bottom" }}>
                    <PageSection>
                        <ActionList>
                            <ActionListGroup>
                                <ActionListItem>
                                    <Button
                                        variant="primary"
                                        onClick={() => setShowFilters(false)}
                                    >
                                        {t("filters.apply-filters", {
                                            count: totalItems,
                                        })}
                                    </Button>
                                </ActionListItem>
                                <ActionListItem>
                                    <Button
                                        variant="link"
                                        onClick={handleClearFilters}
                                    >
                                        {t("filters.clear-all")}
                                    </Button>
                                </ActionListItem>
                            </ActionListGroup>
                        </ActionList>
                    </PageSection>
                </PageGroup>
            </Fragment>
        );
    }

    return (
        <Fragment>
            <OuterScrollContainer>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>{toolbar}</PageSection>
                </PageGroup>
                <InnerScrollContainer
                    style={{
                        marginLeft: 20,
                        marginRight: 20,
                        marginTop: 10,
                        marginBottom: 10,
                    }}
                >
                    <HitsTable
                        state={state}
                        dispatch={dispatch}
                        isLoading={isLoading}
                        isError={isError}
                        error={error}
                        hits={hits}
                        getColumnLabel={(key) =>
                            t(`fields.${key.replaceAll("_", "-")}`)
                        }
                        renderCell={(key, hit) => {
                            switch (key) {
                                case "id":
                                    return <RecordId recordId={hit._id} />;
                                case "base":
                                    return (
                                        <MonospaceValue
                                            value={hit._source.base!}
                                        />
                                    );
                                case "system_number":
                                    return (
                                        <MonospaceValue
                                            value={hit._source.system_number!}
                                        />
                                    );
                                case "title":
                                    return (
                                        <MarcTitle
                                            title={hit._source.title!}
                                            subtitle={hit._source.subtitle}
                                        />
                                    );
                                case "state":
                                    return <RecordStateLabelGroup hit={hit} />;
                                case "authority_links":
                                    return (
                                        <AuthorityLinkLabelGroup hit={hit} />
                                    );
                                case "comparisons":
                                    return <ComparisonLabelGroup hit={hit} />;
                                case "validations":
                                    return <ValidationLabelGroup hit={hit} />;
                                case "latest_sync":
                                    return hit._source.latest_sync ? (
                                        <LocalizedDateTime
                                            date={hit._source.latest_sync}
                                        />
                                    ) : null;
                                case "latest_transaction":
                                    return hit._source.latest_transaction ? (
                                        <LocalizedDateTime
                                            date={
                                                hit._source.latest_transaction
                                            }
                                        />
                                    ) : null;
                            }
                            return null;
                        }}
                        texts={{
                            noMatchFound: {
                                title: t("statement.no-records-found"),
                                body: t("statement.no-records-found-body"),
                            },
                        }}
                    />
                </InnerScrollContainer>
                <PageGroup stickyOnBreakpoint={{ default: "bottom" }}>
                    <PageSection>
                        <Pagination
                            style={{ marginLeft: 20, marginRight: 20 }}
                            perPageOptions={state.config.perPage.options.map(
                                (o) => ({
                                    value: o,
                                    title: o.toString(),
                                })
                            )}
                            itemCount={totalItems}
                            page={state.page}
                            perPage={state.perPage}
                            onSetPage={(_event, newPage, newPerPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                            onPerPageSelect={(_event, newPerPage, newPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                            variant="bottom"
                            titles={{
                                perPageSuffix: t("pagination.per-page-suffix"),
                                ofWord: t("pagination.of-word"),
                            }}
                        />
                    </PageSection>
                </PageGroup>
            </OuterScrollContainer>
        </Fragment>
    );
};

export default RecordsTable;
