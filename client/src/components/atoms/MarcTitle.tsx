import { Content, Stack, StackItem, Truncate } from "@patternfly/react-core";

interface MarcTitleProps {
    title: string;
    subtitle?: string;
}

const MarcTitle = ({ title, subtitle }: MarcTitleProps) => {
    return (
        <Stack>
            <StackItem>
                <Truncate content={title} />
            </StackItem>
            {subtitle && (
                <StackItem>
                    <Content component="small">
                        <Truncate content={subtitle} />
                    </Content>
                </StackItem>
            )}
        </Stack>
    );
};

export default MarcTitle;
