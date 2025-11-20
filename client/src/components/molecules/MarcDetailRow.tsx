import { Td, Tr } from "@patternfly/react-table";
import { useState, type ReactNode } from "react";
import { Button, Stack, StackItem } from "@patternfly/react-core";

interface MarcDetailRowProps {
    key?: string | number;
    children: ReactNode;
    showMoreContent?: ReactNode;
    showMoreDefault?: boolean;
    alwaysShowMore?: boolean;
    showMoreMessage?: string;
    showLessMessage?: string;
}

const MarcDetailRow = ({
    key,
    children,
    showMoreContent,
    showMoreDefault = false,
    alwaysShowMore = false,
    showMoreMessage = "Show more",
    showLessMessage = "Show less",
}: MarcDetailRowProps) => {
    const [showMore, setShowMore] = useState<boolean>(showMoreDefault);

    if (!showMoreContent) {
        return (
            <Tr key={key}>
                <Td colSpan={3}>{children}</Td>
            </Tr>
        );
    }

    return (
        <Tr key={key}>
            <Td colSpan={3}>
                <Stack hasGutter>
                    <StackItem>{children}</StackItem>
                    {(showMore || alwaysShowMore) && (
                        <StackItem>{showMoreContent}</StackItem>
                    )}
                    {!alwaysShowMore && (
                        <StackItem>
                            <Button
                                variant="link"
                                onClick={() => setShowMore(!showMore)}
                            >
                                {showMore ? showLessMessage : showMoreMessage}
                            </Button>
                        </StackItem>
                    )}
                </Stack>
            </Td>
        </Tr>
    );
};

export default MarcDetailRow;
