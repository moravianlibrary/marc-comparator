import {
    MenuToggle,
    Select,
    SelectList,
    SelectOption,
    type MenuToggleElement,
} from "@patternfly/react-core";
import { useState } from "react";
import type { UiText } from "../../models/ui/text";

interface SingleSelectProps {
    options: UiText[];
    icon: React.ReactNode;
    compact?: boolean;
    selected: UiText;
    onSelect: (option: UiText) => void;
}

const SingleSelect = ({
    options,
    icon,
    compact,
    selected,
    onSelect,
}: SingleSelectProps) => {
    const [isOpen, setIsOpen] = useState(false);

    const onSelectChange = (value: string | undefined) => {
        if (value) {
            onSelect(value);
        }
        setIsOpen(false);
    };

    return (
        <Select
            id="option-variations-select"
            isOpen={isOpen}
            selected={selected}
            onSelect={(_event, value) => onSelectChange(value as string)}
            onOpenChange={(isOpen) => setIsOpen(isOpen)}
            toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                    ref={toggleRef}
                    icon={icon}
                    onClick={() => setIsOpen(!isOpen)}
                    isExpanded={isOpen}
                >
                    {!compact && selected.toString()}
                </MenuToggle>
            )}
            shouldFocusToggleOnSelect
        >
            <SelectList>
                {options.map((option) => (
                    <SelectOption key={option.toString()} value={option}>
                        {option.toString()}
                    </SelectOption>
                ))}
            </SelectList>
        </Select>
    );
};

export default SingleSelect;
