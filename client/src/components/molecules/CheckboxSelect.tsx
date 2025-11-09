import { ReactElement, useState } from "react";
import {
    Select,
    SelectList,
    SelectOption,
    MenuToggle,
    type MenuToggleElement,
    Badge,
} from "@patternfly/react-core";

interface Option<T extends string | number = string> {
    value: T;
    label: string;
}

interface CheckboxSelectProps<T extends string | number = string> {
    placeholder: string;
    options: Option<T>[];
    selected: Option<T>[];
    onChange: (selected: Option<T>[]) => void;
}

const CheckboxSelect = <T extends string | number = string>({
    placeholder,
    options,
    selected,
    onChange,
}: CheckboxSelectProps<T>): ReactElement => {
    const [isOpen, setIsOpen] = useState(false);

    const onSelect = (
        _event: React.MouseEvent<Element, MouseEvent> | undefined,
        value: string | number | undefined
    ) => {
        if (value === undefined) return;

        const isAlreadySelected = selected.some((s) => s.value === value);

        if (isAlreadySelected) {
            onChange(selected.filter((s) => s.value !== value));
        } else {
            const option = options.find((o) => o.value === value);
            if (option) {
                onChange([...selected, option]);
            }
        }
    };

    const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen((prev) => !prev)}
            isExpanded={isOpen}
        >
            {placeholder}
            {selected.length > 0 && (
                <Badge isRead style={{ marginLeft: 8 }}>
                    {selected.length}
                </Badge>
            )}
        </MenuToggle>
    );

    return (
        <Select
            id="checkbox-select"
            role="menu"
            isOpen={isOpen}
            onSelect={onSelect}
            onOpenChange={setIsOpen}
            toggle={toggle}
        >
            <SelectList>
                {options.map((option) => (
                    <SelectOption
                        key={option.value}
                        hasCheckbox
                        value={option.value}
                        isSelected={selected.some(
                            (s) => s.value === option.value
                        )}
                    >
                        {option.label}
                    </SelectOption>
                ))}
            </SelectList>
        </Select>
    );
};

export default CheckboxSelect;
