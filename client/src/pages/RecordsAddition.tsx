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

// ------------------------------------
// Add One Record Card
// ------------------------------------
const AddOneRecordCard = (): ReactElement => {
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
            <CardTitle>Add One Record</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Add a single record to the database by selecting a base
                        and entering the system number.
                    </p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            Enter system number
                        </DescriptionListTerm>
                        <DescriptionListDescription>
                            <TextInput
                                id="system-number-input"
                                value={systemNumber}
                                type="text"
                                placeholder="Enter system number"
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
                    Add Record
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Add Batch of Records Card
// ------------------------------------
const AddBatchOfRecordsCard = (): ReactElement => {
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
            <CardTitle>Add Batch of Records</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Add multiple records to the database by selecting a base
                        and uploading a file containing system numbers.
                    </p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            Upload system numbers file
                        </DescriptionListTerm>
                        <DescriptionListDescription>
                            <FileUpload
                                id="batch-upload"
                                type="text"
                                value={value}
                                filename={filename}
                                filenamePlaceholder="Drag and drop a file or upload one"
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
                                browseButtonText="Upload"
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
                    Add Records
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Sync Records from Catalog Card
// ------------------------------------
const SyncRecordsFromCatalogCard = (): ReactElement => {
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
            <CardTitle>Sync Records from Catalog</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Sync records from the external catalog into the local
                        database by selecting a base and optionally providing a
                        start date.
                    </p>
                </Content>
            </CardBody>

            <CardBody>
                <DescriptionList>
                    <CatalogBaseSelector selected={base} onChange={setBase} />
                    <DescriptionListGroup>
                        <DescriptionListTerm>
                            From Date (optional)
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
                                    placeholder="Select from date"
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
                    Sync Records
                </Button>
            </CardFooter>
        </Card>
    );
};

// ------------------------------------
// Main Page
// ------------------------------------
const RecordsAddition = (): ReactElement => (
    <>
        <PageGroup stickyOnBreakpoint={{ default: "top" }}>
            <PageSection>
                <Content>
                    <h1>Records Addition</h1>
                    <p>
                        Add, batch upload, or sync records for selected bases.
                    </p>
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

export default RecordsAddition;
