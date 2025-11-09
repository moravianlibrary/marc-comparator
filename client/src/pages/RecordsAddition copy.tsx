import {
    Button,
    Card,
    CardBody,
    CardTitle,
    Content,
    DatePicker,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    type DropEvent,
    FileUpload,
    Gallery,
    PageGroup,
    PageSection,
    Spinner,
    TextInput,
} from "@patternfly/react-core";
import { ChangeEvent, Fragment, ReactElement, useState } from "react";
import { useGetSystemInfo } from "../hooks/useSystem";
import SingleSelect from "../components/molecules/SingleSelect";
import {
    useAddBatchOfRecords,
    useAddOneRecord,
    useSyncRecords,
} from "../hooks/useCatalogRecords";
import { TimesIcon } from "@patternfly/react-icons";

const AddOneRecordCard = (): ReactElement => {
    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    const addOneRecordMutation = useAddOneRecord();

    const [selectedBase, setSelectedBase] = useState<{
        label: string;
        value: string;
    } | null>(null);
    const [systemNumber, setSystemNumber] = useState("");

    const isValidSystemNumber = /^\d{9}$/.test(systemNumber);

    const handleAddRecord = () => {
        if (selectedBase && isValidSystemNumber) {
            addOneRecordMutation.mutate({
                base: selectedBase.value,
                systemNumber: systemNumber,
            });
        }
    };

    const selectBaseGroup = (
        <DescriptionListGroup>
            <DescriptionListTerm>Select base</DescriptionListTerm>
            <DescriptionListDescription>
                <SingleSelect
                    placeholder="Select base"
                    options={
                        availableBases?.map((base) => ({
                            label: base,
                            value: base,
                        })) ?? []
                    }
                    selected={selectedBase}
                    onChange={setSelectedBase}
                />
            </DescriptionListDescription>
        </DescriptionListGroup>
    );

    const enterSystemNumberGroup = (
        <DescriptionListGroup>
            <DescriptionListTerm>Enter system number</DescriptionListTerm>
            <DescriptionListDescription>
                <TextInput
                    value={systemNumber}
                    type="text"
                    onChange={(_event, value) => setSystemNumber(value)}
                    placeholder="Enter system number"
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
    );

    return (
        <Card>
            <CardTitle>Add One Record</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Add a single record to the database by selecting
                        specific base and entering the system number.
                    </p>
                </Content>
            </CardBody>
            <CardBody>
                {isLoading ? (
                    <Spinner size="lg" />
                ) : (
                    <DescriptionList>
                        {selectBaseGroup}
                        {enterSystemNumberGroup}
                    </DescriptionList>
                )}
            </CardBody>
            <CardBody>
                <Button
                    variant="primary"
                    isDisabled={
                        !selectedBase || !systemNumber || !isValidSystemNumber
                    }
                    onClick={handleAddRecord}
                >
                    Add Record
                </Button>
            </CardBody>
        </Card>
    );
};

const AddBatchOfRecordsCard = (): ReactElement => {
    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    const addBatchMutation = useAddBatchOfRecords();

    const [selectedBase, setSelectedBase] = useState<{
        label: string;
        value: string;
    } | null>(null);
    const [filename, setFilename] = useState<string>("");
    const [value, setValue] = useState<string>("");
    const [isUploading, setIsUploading] = useState<boolean>(false);

    const hasValidSystemNumbers = value
        .split("\n")
        .every((line) => /^\d{9}$/.test(line) || line.trim() === "");

    // ---- Handlers ----
    const handleFileInputChange = (_event: DropEvent, file: File) => {
        setFilename(file.name);
    };

    const handleDataChange = (_event: DropEvent, value: string) => {
        setValue(value);
    };

    const handleTextChange = (
        _event: ChangeEvent<HTMLTextAreaElement>,
        value: string
    ) => {
        setValue(value);
    };

    const handleClear = () => {
        setFilename("");
        setValue("");
        setIsUploading(false);
    };

    const handleAddRecords = () => {
        if (selectedBase && hasValidSystemNumbers) {
            const systemNumbers = value
                .split("\n")
                .map((line) => line.trim())
                .filter((line) => line !== "");
            addBatchMutation.mutate({
                per_base: {
                    base: selectedBase.value,
                    systemNumbers: systemNumbers,
                },
            });
        }
    };

    const selectBaseGroup = (
        <DescriptionListGroup>
            <DescriptionListTerm>Select base</DescriptionListTerm>
            <DescriptionListDescription>
                <SingleSelect
                    placeholder="Select base"
                    options={
                        availableBases?.map((base) => ({
                            label: base,
                            value: base,
                        })) ?? []
                    }
                    selected={selectedBase}
                    onChange={setSelectedBase}
                />
            </DescriptionListDescription>
        </DescriptionListGroup>
    );

    return (
        <Card>
            <CardTitle>Add Batch of Records</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Add multiple records to the database by specifying base
                        and uploading a file containing system numbers.
                    </p>
                </Content>
            </CardBody>
            <CardBody>
                {isLoading ? (
                    <Spinner size="lg" />
                ) : (
                    <DescriptionList>
                        {selectBaseGroup}
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                Upload system numbers file
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                <FileUpload
                                    id="text-file-with-edits-allowed-example"
                                    type="text"
                                    value={value}
                                    filename={filename}
                                    filenamePlaceholder="Drag and drop a file or upload one"
                                    onFileInputChange={handleFileInputChange}
                                    onDataChange={handleDataChange}
                                    onTextChange={handleTextChange}
                                    onReadStarted={() => setIsUploading(true)}
                                    onReadFinished={() => setIsUploading(false)}
                                    onClearClick={handleClear}
                                    isLoading={isUploading}
                                    allowEditingUploadedText={true}
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
                )}
            </CardBody>
            <CardBody>
                <Button
                    variant="primary"
                    isDisabled={
                        !selectedBase || !value || !hasValidSystemNumbers
                    }
                    onClick={handleAddRecords}
                >
                    Add Records
                </Button>
            </CardBody>
        </Card>
    );
};

const SyncRecordsFromCatalogCard = (): ReactElement => {
    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    const syncRecordsFromCatalogMutation = useSyncRecords();

    const [selectedBase, setSelectedBase] = useState<{
        label: string;
        value: string;
    } | null>(null);
    const [fromDate, setFromDate] = useState<Date | undefined>(undefined);

    const validateDate = (selectedDate: Date) => {
        if (selectedDate > new Date()) {
            return "From date cannot be in the future.";
        }
        return "";
    };

    const handleSyncRecords = () => {
        if (selectedBase) {
            syncRecordsFromCatalogMutation.mutate({
                base: selectedBase.value,
                from_date: fromDate,
            });
        }
    };

    const selectBaseGroup = (
        <DescriptionListGroup>
            <DescriptionListTerm>Select base</DescriptionListTerm>
            <DescriptionListDescription>
                <SingleSelect
                    placeholder="Select base"
                    options={
                        availableBases?.map((base) => ({
                            label: base,
                            value: base,
                        })) ?? []
                    }
                    selected={selectedBase}
                    onChange={setSelectedBase}
                />
            </DescriptionListDescription>
        </DescriptionListGroup>
    );

    return (
        <Card>
            <CardTitle>Sync Records from Catalog</CardTitle>
            <CardBody>
                <Content>
                    <p>
                        Sync records from the external catalog into the local
                        database by selecting the desired base and initiating
                        the sync process.
                    </p>
                </Content>
            </CardBody>
            <CardBody>
                {isLoading ? (
                    <Spinner size="lg" />
                ) : (
                    <DescriptionList>
                        {selectBaseGroup}
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                From Date (optional)
                            </DescriptionListTerm>
                            <DescriptionListDescription>
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
                                    isInline
                                    onClick={() => setFromDate(undefined)}
                                    icon={<TimesIcon />}
                                    style={{ marginLeft: "5px" }}
                                />
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                    </DescriptionList>
                )}
            </CardBody>
            <CardBody>
                <Button
                    variant="primary"
                    isDisabled={!selectedBase}
                    onClick={handleSyncRecords}
                >
                    Sync Records
                </Button>
            </CardBody>
        </Card>
    );
};

const RecordsAddition = (): ReactElement => {
    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>Records Addition</h1>
                        <p></p>
                    </Content>
                </PageSection>
            </PageGroup>

            <PageSection>
                <Gallery
                    hasGutter
                    minWidths={{ default: "400px" }}
                    maxWidths={{ default: "1200px" }}
                >
                    <AddOneRecordCard />
                    <AddBatchOfRecordsCard />
                    <SyncRecordsFromCatalogCard />
                </Gallery>
            </PageSection>
        </Fragment>
    );
};

export default RecordsAddition;
