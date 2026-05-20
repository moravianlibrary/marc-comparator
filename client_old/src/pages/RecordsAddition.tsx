import {
    Button,
    Card,
    CardBody,
    CardFooter,
    CardTitle,
    Content,
    DatePicker,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    FileUpload,
    Gallery,
    PageGroup,
    PageSection,
    TextInput,
} from "@patternfly/react-core";
import { TimesIcon } from "@patternfly/react-icons";
import { type ReactElement, useState } from "react";
import {
    useAddBatchOfRecords,
    useAddOneRecord,
    useSyncRecords,
} from "../hooks/useCatalogRecords";
import CatalogBaseSelector from "../components/organisms/CatalogBaseSelector";
import { useTranslation } from "react-i18next";

// ------------------------------------
// Add One Record Card
// ------------------------------------
const AddOneRecordCard = (): ReactElement => {
    const { t } = useTranslation("records-addition");

    const addOneRecord = useAddOneRecord();

    const [base, setBase] = useState<string | null>(null);
    const [systemNumber, setSystemNumber] = useState("");

    const isValidSystemNumber = /^\d{9}$/.test(systemNumber);

    const handleAddRecord = () => {
        if (base && isValidSystemNumber) {
            addOneRecord.mutate({ base, system_number: systemNumber });
        }
    };

    return (
        <Card>
            <CardTitle>{t("add-one-record.title")}</CardTitle>
            <CardBody>
                <Content>
                    <p>{t("add-one-record.description")}</p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            {t("add-one-record.enter-system-number")}
                        </DescriptionListTerm>
                        <DescriptionListDescription>
                            <TextInput
                                id="system-number-input"
                                value={systemNumber}
                                type="text"
                                placeholder={t(
                                    "add-one-record.enter-system-number"
                                )}
                                onChange={(_, value) => setSystemNumber(value)}
                                validated={
                                    systemNumber
                                        ? isValidSystemNumber
                                            ? "success"
                                            : "error"
                                        : "default"
                                }
                            />
                        </DescriptionListDescription>
                    </DescriptionListGroup>
                </DescriptionList>
            </CardBody>

            <CardFooter>
                <Button
                    variant="primary"
                    isDisabled={!base || !isValidSystemNumber}
                    onClick={handleAddRecord}
                >
                    {t("add-one-record.add-button")}
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Add Batch of Records Card
// ------------------------------------
const AddBatchOfRecordsCard = (): ReactElement => {
    const { t } = useTranslation("records-addition");

    const addBatchRecords = useAddBatchOfRecords();

    const [base, setBase] = useState<string | null>(null);
    const [filename, setFilename] = useState("");
    const [value, setValue] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    const hasValidSystemNumbers = value
        .split("\n")
        .every((line) => /^\d{9}$/.test(line.trim()) || line.trim() === "");

    const handleAddRecords = () => {
        if (base && hasValidSystemNumbers) {
            const systemNumbers = value
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean);

            addBatchRecords.mutate({
                per_base: { base, system_numbers: systemNumbers },
            });
        }
    };

    const clearFile = () => {
        setFilename("");
        setValue("");
        setIsUploading(false);
    };

    return (
        <Card>
            <CardTitle>{t("add-batch-of-records.title")}</CardTitle>
            <CardBody>
                <Content>
                    <p>{t("add-batch-of-records.description")}</p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            {t("add-batch-of-records.upload-file")}
                        </DescriptionListTerm>
                        <DescriptionListDescription>
                            <FileUpload
                                id="batch-upload"
                                type="text"
                                value={value}
                                filename={filename}
                                filenamePlaceholder={t(
                                    "add-batch-of-records.upload-file-placeholder"
                                )}
                                onFileInputChange={(_, file) =>
                                    setFilename(file.name)
                                }
                                onDataChange={(_, val) => setValue(val)}
                                onTextChange={(_, val) => setValue(val)}
                                onReadStarted={() => setIsUploading(true)}
                                onReadFinished={() => setIsUploading(false)}
                                onClearClick={clearFile}
                                isLoading={isUploading}
                                allowEditingUploadedText
                                browseButtonText={t(
                                    "add-batch-of-records.browse-button"
                                )}
                                clearButtonText={t(
                                    "add-batch-of-records.clear-button"
                                )}
                                validated={
                                    value
                                        ? hasValidSystemNumbers
                                            ? "success"
                                            : "error"
                                        : "default"
                                }
                            />
                        </DescriptionListDescription>
                    </DescriptionListGroup>
                </DescriptionList>
            </CardBody>

            <CardFooter>
                <Button
                    variant="primary"
                    isDisabled={!base || !value || !hasValidSystemNumbers}
                    onClick={handleAddRecords}
                >
                    {t("add-batch-of-records.add-button")}
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Sync Records from Catalog Card
// ------------------------------------
const SyncRecordsFromCatalogCard = (): ReactElement => {
    const { t } = useTranslation("records-addition");

    const syncRecords = useSyncRecords();

    const [base, setBase] = useState<string | null>(null);
    const [fromDate, setFromDate] = useState<Date | undefined>(undefined);

    const validateDate = (selectedDate: Date) =>
        selectedDate > new Date() ? "From date cannot be in the future." : "";

    const handleSyncRecords = () => {
        if (base) syncRecords.mutate({ base, from_date: fromDate });
    };

    return (
        <Card>
            <CardTitle>{t("sync-from-catalog.title")}</CardTitle>
            <CardBody>
                <Content>
                    <p>{t("sync-from-catalog.description")}</p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            {t("sync-from-catalog.from-date")}
                        </DescriptionListTerm>
                        <DescriptionListDescription>
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "8px",
                                }}
                            >
                                <DatePicker
                                    value={fromDate?.toISOString().slice(0, 10)}
                                    placeholder={t(
                                        "sync-from-catalog.from-date-placeholder"
                                    )}
                                    appendTo={() => document.body}
                                    validators={[validateDate]}
                                    onChange={(_, __, newDate) =>
                                        newDate && setFromDate(newDate)
                                    }
                                />
                                <Button
                                    variant="control"
                                    icon={<TimesIcon />}
                                    onClick={() => setFromDate(undefined)}
                                    aria-label="Clear date"
                                />
                            </div>
                        </DescriptionListDescription>
                    </DescriptionListGroup>
                </DescriptionList>
            </CardBody>

            <CardFooter>
                <Button
                    variant="primary"
                    isDisabled={!base}
                    onClick={handleSyncRecords}
                >
                    {t("sync-from-catalog.sync-button")}
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Main Page
// ------------------------------------
const RecordsAddition = (): ReactElement => {
    const { t } = useTranslation("records-addition");

    return (
        <>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>{t("title")}</h1>
                        <p>{t("description")}</p>
                    </Content>
                </PageSection>
            </PageGroup>

            <PageSection isFilled>
                <Gallery
                    hasGutter
                    minWidths={{
                        default: "500px",
                        sm: "100%",
                        md: "500px",
                        lg: "500px",
                        xl: "600px",
                    }}
                    maxWidths={{
                        default: "1fr",
                        sm: "100%",
                        md: "1fr",
                        lg: "1fr",
                        xl: "1fr",
                    }}
                >
                    <AddOneRecordCard />
                    <AddBatchOfRecordsCard />
                    <SyncRecordsFromCatalogCard />
                </Gallery>
            </PageSection>
        </>
    );
};

export default RecordsAddition;
