import { useState, type ReactElement } from "react";
import type { CollectionFilterProps } from "../atoms/CollectionFilterProps";
import {
    Select,
    MenuToggle,
    SelectList,
    SelectOption,
    type MenuToggleElement,
    Badge,
} from "@patternfly/react-core";
import type { TermsFilterState } from "../../models/ui/filters";

interface TermFilterCheckboxMenuProps<T> extends CollectionFilterProps<T> {}

const TermFilterCheckboxMenu = <T,>({
    field,
    config: { filter },
    state: { filterStates },
    data: { aggregations },
    dispatch,
}: TermFilterCheckboxMenuProps<T>): ReactElement => {
    const [isOpen, setIsOpen] = useState<boolean>(false);

    const selectedItems: string[] =
        (filterStates?.[field] as TermsFilterState).include ?? [];

    const onToggleClick = () => setIsOpen(!isOpen);

    const onSelect = (
        _event: React.MouseEvent<Element, MouseEvent> | undefined,
        value: string | number
    ) => {
        if (selectedItems.includes(String(value))) {
            dispatch({ type: "toggleTerm", field, bucketKey: String(value) });
        } else {
            dispatch({ type: "toggleTerm", field, bucketKey: String(value) });
        }
    };

    const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
            ref={toggleRef}
            onClick={onToggleClick}
            isExpanded={isOpen}
            style={
                {
                    width: "200px",
                } as React.CSSProperties
            }
        >
            Filter by status
            {selectedItems.length > 0 && (
                <Badge isRead>{selectedItems.length}</Badge>
            )}
        </MenuToggle>
    );

    return (
        <Select
            role="menu"
            id="checkbox-select"
            isOpen={isOpen}
            selected={selectedItems}
            onSelect={onSelect}
            onOpenChange={(nextOpen: boolean) => setIsOpen(nextOpen)}
            toggle={toggle}
        >
            <SelectList>
                <SelectOption
                    hasCheckbox
                    value={0}
                    isSelected={selectedItems.includes(0)}
                >
                    Debug
                </SelectOption>
                <SelectOption
                    hasCheckbox
                    value={1}
                    isSelected={selectedItems.includes(1)}
                >
                    Info
                </SelectOption>
                <SelectOption
                    hasCheckbox
                    value={2}
                    isSelected={selectedItems.includes(2)}
                >
                    Warn
                </SelectOption>
                <SelectOption
                    hasCheckbox
                    isDisabled
                    value={4}
                    isSelected={selectedItems.includes(4)}
                >
                    Error
                </SelectOption>
            </SelectList>
        </Select>
    );
};

export default TermFilterCheckboxMenu;
