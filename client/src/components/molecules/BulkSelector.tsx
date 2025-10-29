import {
    Dropdown,
    DropdownItem,
    DropdownList,
    MenuToggle,
    MenuToggleCheckbox,
} from "@patternfly/react-core";
import { useState } from "react";
import type { DynamicUiText, StaticUiText } from "../../models/ui/text";

export interface BulkSelectorTexts {
    selectNone: StaticUiText;
    selectPage: DynamicUiText;
    selectAll: DynamicUiText;
    selectedCount: DynamicUiText;
}

interface BulkSelectorProps {
    selectedCount: number;
    onPageCount: number;
    totalCount: number;
    onSelectNone: () => void;
    onSelectPage: () => void;
    onSelectAll: () => void;
    texts: BulkSelectorTexts;
}

interface SelectCallbackItem {
    key: string;
    label: string;
    onClick: () => void;
}

const BulkSelector = ({
    selectedCount,
    onPageCount,
    totalCount,
    onSelectNone,
    onSelectPage,
    onSelectAll,
    texts,
}: BulkSelectorProps) => {
    const anySelected = selectedCount > 0;
    const allSelected = selectedCount > 0 && selectedCount === totalCount;

    const selectOptions: SelectCallbackItem[] = [
        {
            key: "select-none",
            label: texts.selectNone,
            onClick: onSelectNone,
        },
        {
            key: "select-page",
            label: texts.selectPage({ count: onPageCount }),
            onClick: onSelectPage,
        },
        {
            key: "select-all",
            label: texts.selectAll({ count: totalCount }),
            onClick: onSelectAll,
        },
    ];

    const [isOpen, setIsOpen] = useState<boolean>(false);

    return (
        <Dropdown
            onSelect={() => setIsOpen(false)}
            isOpen={isOpen}
            onOpenChange={setIsOpen}
            toggle={(toggleRef) => (
                <MenuToggle
                    ref={toggleRef}
                    isExpanded={anySelected}
                    onClick={() => setIsOpen(!isOpen)}
                    splitButtonItems={[
                        <MenuToggleCheckbox
                            id="split-dropdown-checkbox"
                            key="split-dropdown-checkbox"
                            isChecked={
                                allSelected ? true : anySelected ? null : false
                            }
                            onClick={() => {
                                setIsOpen(false);
                                allSelected ? onSelectNone() : onSelectAll();
                            }}
                        >
                            <span style={{ whiteSpace: "nowrap" }}>
                                {selectedCount !== 0 &&
                                    texts.selectedCount({
                                        count: selectedCount,
                                    })}
                            </span>
                        </MenuToggleCheckbox>,
                    ]}
                />
            )}
        >
            <DropdownList>
                {selectOptions.map(({ key, label, onClick }) => (
                    <DropdownItem key={key} onClick={onClick}>
                        {label}
                    </DropdownItem>
                ))}
            </DropdownList>
        </Dropdown>
    );
};

export default BulkSelector;
