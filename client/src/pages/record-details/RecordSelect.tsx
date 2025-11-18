import {
    Button,
    Form,
    FormSelect,
    FormSelectOption,
    HelperText,
    HelperTextItem,
    Split,
    SplitItem,
    TextInput,
} from "@patternfly/react-core";
import { useEffect, useState, type ReactElement } from "react";
import { ArrowRightIcon } from "@patternfly/react-icons";

interface RecordSelectProps {
    availableBases: string[];
    base: string | null;
    systemNumber: string | null;
    onSubmit: (base: string, systemNumber: string) => void;
}

const RecordSelect = ({
    availableBases,
    base,
    systemNumber,
    onSubmit,
}: RecordSelectProps): ReactElement => {
    const [baseState, setBase] = useState<string>(base || "");
    const [systemNumberState, setSystemNumber] = useState<string>(
        systemNumber || ""
    );

    useEffect(() => {
        setBase(base || "");
    }, [base]);

    useEffect(() => {
        setSystemNumber(systemNumber || "");
    }, [systemNumber]);

    const isValidSystemNumber = /^\d{9}$/.test(systemNumberState);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (baseState && systemNumberState) {
            onSubmit(baseState, systemNumberState);
        }
    };

    return (
        <Form isHorizontal onSubmit={handleSubmit}>
            <Split hasGutter>
                <SplitItem>
                    <FormSelect
                        id="base-select"
                        value={baseState}
                        onChange={(_, value) => setBase(value)}
                        placeholder="Select base"
                    >
                        <FormSelectOption
                            key="empty"
                            value=""
                            label="Select base"
                            isPlaceholder
                        />
                        {availableBases.map((b, i) => (
                            <FormSelectOption key={i} value={b} label={b} />
                        ))}
                    </FormSelect>
                </SplitItem>

                <SplitItem>
                    <TextInput
                        id="system-number-input"
                        value={systemNumberState}
                        type="text"
                        onChange={(_, value) => setSystemNumber(value)}
                        placeholder="Enter system number"
                        validated={
                            systemNumberState
                                ? isValidSystemNumber
                                    ? "success"
                                    : "error"
                                : "default"
                        }
                        width="100%"
                    />
                    {systemNumber && !isValidSystemNumber && (
                        <HelperText>
                            <HelperTextItem variant="error">
                                System number must be exactly 9 digits.
                            </HelperTextItem>
                        </HelperText>
                    )}
                </SplitItem>
                <SplitItem>
                    <Button
                        id="submit-button"
                        variant="control"
                        icon={<ArrowRightIcon />}
                        type="submit"
                        disabled={!base || !isValidSystemNumber}
                    />
                </SplitItem>
            </Split>
        </Form>
    );
};

export default RecordSelect;
