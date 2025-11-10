import { Stack, StackItem, Switch } from "@patternfly/react-core";

interface ToggleListProps {
    options: {
        id: string;
        label: string;
        isChecked: boolean;
        isDisabled?: boolean;
    }[];
    onToggle: (id: string, isChecked: boolean) => void;
}

export const ToggleList = ({ options, onToggle }: ToggleListProps) => (
    <Stack hasGutter>
        {options.map(({ id, label, isChecked, isDisabled }) => (
            <StackItem key={id}>
                <Switch
                    id={id}
                    label={label}
                    isChecked={isChecked}
                    isDisabled={isDisabled}
                    onChange={(_, checked) => onToggle(id, checked)}
                />
            </StackItem>
        ))}
    </Stack>
);

export default ToggleList;
