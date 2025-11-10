import { ReactElement, useState } from "react";
import {
    Select,
    SelectList,
    SelectOption,
    MenuToggle,
    type MenuToggleElement,
    type PopperOptions,
} from "@patternfly/react-core";

interface Option<T extends string | number = string> {
    value: T;
    label: string;
}

interface SingleSelectProps<T extends string | number = string> {
    placeholder: string;
    options: Option<T>[];
    selected?: Option<T> | null;
    onChange: (selected: Option<T> | null) => void;
    icon?: ReactElement;
    isDisabled?: boolean;
    popperProps?: PopperOptions;
}

const SingleSelect = <T extends string | number = string>({
    placeholder,
    options,
    selected,
    onChange,
    icon,
    isDisabled = false,
    popperProps,
}: SingleSelectProps<T>): ReactElement => {
    const [isOpen, setIsOpen] = useState(false);

    const onSelect = (
        _event: React.MouseEvent<Element, MouseEvent> | undefined,
        value: string | number | undefined
    ) => {
        if (value === undefined) return;
        const newSelection =
            selected?.value === value
                ? null
                : options.find((o) => o.value === value) ?? null;
        onChange(newSelection);
        setIsOpen(false);
    };

    const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen((prev) => !prev)}
            icon={icon}
            isExpanded={isOpen}
            isDisabled={isDisabled}
        >
            {selected ? selected.label : placeholder}
        </MenuToggle>
    );

    return (
        <Select
            id="option-select"
            isOpen={isOpen}
            onOpenChange={setIsOpen}
            onSelect={onSelect}
            toggle={toggle}
            popperProps={popperProps}
        >
            <SelectList>
                {options.map((option) => (
                    <SelectOption
                        key={option.value}
                        value={option.value}
                        isSelected={selected?.value === option.value}
                    >
                        {option.label}
                    </SelectOption>
                ))}
            </SelectList>
        </Select>
    );
};

export default SingleSelect;
