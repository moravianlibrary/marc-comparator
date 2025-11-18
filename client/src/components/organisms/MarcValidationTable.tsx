import { Table, Tbody, Td, Tr } from "@patternfly/react-table";
import { useState, type JSX, type ReactElement } from "react";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
import {
    Bullseye,
    Button,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    EmptyState,
    HelperText,
    Spinner,
    Stack,
    StackItem,
} from "@patternfly/react-core";
import MonospaceValue from "../atoms/MonospaceValue";
import type { Validation } from "../../models/api/responses/validation";
import ValidityHelperTextItem from "../atoms/ValidityHelperTextItem";

interface MarcValidationTableProps {
    base?: string;
    systemNumber?: string;
    noMarcRecordMessage?: string;
    validations?: Validation[];
    showOnlyTarget?: boolean;
}

const MarcValidationTable = ({
    base,
    systemNumber,
    noMarcRecordMessage = "No MARC record available",
    validations,
    showOnlyTarget,
}: MarcValidationTableProps): ReactElement => {
    const { data, isLoading } = useGetMarcRecord(
        base || "",
        systemNumber || "",
        !!base && !!systemNumber
    );

    const [showMore, setShowMore] = useState<Set<string>>(new Set());

    const toggleShowMore = (key: string) => {
        setShowMore((prev) => {
            const newSet = new Set(prev);
            if (newSet.has(key)) {
                newSet.delete(key);
            } else {
                newSet.add(key);
            }
            return newSet;
        });
    };

    if (!validations) {
        return <Bullseye>No validations provided</Bullseye>;
    }

    const validationsLookup = validations.reduce<Record<string, Validation>>(
        (acc, validation) => {
            const tag = validation.target.tag;
            acc[tag] = validation;
            return acc;
        },
        {}
    );

    const getFixedFieldRow = (tag: string, value: string, index: number) => (
        <Tr key={`fixed-field-${index}`}>
            <Td>
                <MonospaceValue value={tag} />
            </Td>
            <Td></Td>
            <Td></Td>
            <Td>
                <MonospaceValue value={value} />
            </Td>
        </Tr>
    );

    const getVariableFieldRow = (
        tag: string,
        ind1: string,
        ind2: string,
        subfields: Record<string, string[]>,
        index: number,
        targetCodes?: string[]
    ) => {
        const codeItems: JSX.Element[] = [];
        const valueItems: JSX.Element[] = [];

        Object.entries(subfields)
            .sort(([a], [b]) => a.localeCompare(b))
            .forEach(([key, values], idx) => {
                codeItems.push(
                    <StackItem key={`key-${idx}`}>
                        <MonospaceValue
                            value={key}
                            bold={targetCodes?.includes(key) ?? false}
                        />
                    </StackItem>
                );
                values.forEach((val, subIdx) => {
                    valueItems.push(
                        <StackItem key={`val-${idx}-${subIdx}`}>
                            <span
                                style={{
                                    fontWeight:
                                        targetCodes?.includes(key) ?? false
                                            ? "bold"
                                            : "normal",
                                }}
                            >
                                {val}
                            </span>
                        </StackItem>
                    );
                });
            });

        return (
            <Tr key={`var-${tag}-${index}`}>
                <Td>
                    <MonospaceValue value={tag} />
                </Td>
                <Td>
                    <MonospaceValue
                        value={`${ind1?.trim() !== "" ? ind1 : "-"}${
                            ind2?.trim() !== "" ? ind2 : "-"
                        }`}
                    />
                </Td>
                <Td>
                    <Stack>{codeItems}</Stack>
                </Td>
                <Td>
                    <Stack>{valueItems}</Stack>
                </Td>
            </Tr>
        );
    };

    const getValidationRow = (tag: string, index: number) => {
        const validation = validationsLookup[tag];
        const showMoreKey = `${tag}-${validation.validator}-${index}`;
        const hasShowMore = showMore.has(showMoreKey);

        return (
            <Tr key={`validation-${index}`}>
                <Td colSpan={4}>
                    <Stack hasGutter>
                        <StackItem>
                            <HelperText>
                                <ValidityHelperTextItem
                                    status={validation.status}
                                    text={
                                        validation.reason ||
                                        "No reason provided"
                                    }
                                />
                            </HelperText>
                        </StackItem>
                        {(showOnlyTarget || hasShowMore) &&
                            (validation.details || validation.hints) && (
                                <StackItem>
                                    <DescriptionList isHorizontal>
                                        {validation.details && (
                                            <DescriptionListGroup>
                                                <DescriptionListTerm>
                                                    Details
                                                </DescriptionListTerm>
                                                <DescriptionListDescription>
                                                    {validation.details}
                                                </DescriptionListDescription>
                                            </DescriptionListGroup>
                                        )}
                                        {validation.hints && (
                                            <DescriptionListGroup>
                                                <DescriptionListTerm>
                                                    Hints
                                                </DescriptionListTerm>
                                                <DescriptionListDescription>
                                                    {validation.hints}
                                                </DescriptionListDescription>
                                            </DescriptionListGroup>
                                        )}
                                    </DescriptionList>
                                </StackItem>
                            )}
                        {!showOnlyTarget &&
                            (validation.details || validation.hints) && (
                                <StackItem>
                                    <Button
                                        variant="link"
                                        onClick={() =>
                                            toggleShowMore(showMoreKey)
                                        }
                                    >
                                        {hasShowMore
                                            ? "Show less"
                                            : "Show more"}
                                    </Button>
                                </StackItem>
                            )}
                    </Stack>
                </Td>
            </Tr>
        );
    };

    return (
        <Table variant="compact">
            {isLoading ? (
                <Tbody>
                    <Tr>
                        <Td colSpan={4}>
                            <Bullseye>
                                <Spinner size="xl" />
                            </Bullseye>
                        </Td>
                    </Tr>
                </Tbody>
            ) : !data ? (
                <Tbody>
                    <Tr>
                        <Td colSpan={4}>
                            <Bullseye>
                                <EmptyState>{noMarcRecordMessage}</EmptyState>
                            </Bullseye>
                        </Td>
                    </Tr>
                </Tbody>
            ) : (
                <Tbody isEvenStriped>
                    <Tr key="id">
                        <Td>
                            <MonospaceValue value="System Number" />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={systemNumber || ""} />
                        </Td>
                    </Tr>
                    {!showOnlyTarget && (
                        <Tr key="leader">
                            <Td>
                                <MonospaceValue value="Leader" />
                            </Td>
                            <Td></Td>
                            <Td></Td>
                            <Td>
                                <MonospaceValue value={data.leader} />
                            </Td>
                        </Tr>
                    )}
                    {Object.entries(data.fixed_fields)
                        .filter(
                            ([tag]) =>
                                !showOnlyTarget || tag in validationsLookup
                        )
                        .sort(([tagA], [tagB]) => tagA.localeCompare(tagB))
                        .flatMap(([tag, value], index) =>
                            tag in validationsLookup
                                ? [
                                      getFixedFieldRow(tag, value, index),
                                      getValidationRow(tag, index),
                                  ]
                                : [getFixedFieldRow(tag, value, index)]
                        )}
                    {Object.entries(data.variable_fields)
                        .filter(
                            ([tag]) =>
                                !showOnlyTarget || tag in validationsLookup
                        )
                        .sort(([tagA], [tagB]) => tagA.localeCompare(tagB))
                        .map(([tag, fields]) =>
                            fields.flatMap(
                                ({ ind1, ind2, subfields }, subIndex) =>
                                    tag in validationsLookup
                                        ? [
                                              getVariableFieldRow(
                                                  tag,
                                                  ind1,
                                                  ind2,
                                                  subfields,
                                                  subIndex
                                              ),
                                              getValidationRow(tag, subIndex),
                                          ]
                                        : [
                                              getVariableFieldRow(
                                                  tag,
                                                  ind1,
                                                  ind2,
                                                  subfields,
                                                  subIndex
                                              ),
                                          ]
                            )
                        )}
                </Tbody>
            )}
        </Table>
    );
};

export default MarcValidationTable;
