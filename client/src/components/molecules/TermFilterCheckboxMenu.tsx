import { useEffect, useRef, useState, type ReactElement } from "react";
import type { CollectionFilterProps } from "../atoms/CollectionFilterProps";
import {
    MenuToggle,
    Badge,
    Popper,
    Menu,
    MenuContent,
    MenuList,
    MenuItem,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import type {
    TermsFilterConfig,
    TermsFilterState,
} from "../../models/ui/filters";
import { FilterIcon } from "@patternfly/react-icons";
import type { EsTermsBucket } from "../../models/api/responses/es_aggregations";

interface TermFilterCheckboxMenuProps<T> extends CollectionFilterProps<T> {}

const TermFilterCheckboxMenu = <T,>({
    field,
    context: {
        config: { filter },
        state: { filterStates },
        data: { aggregations },
        dispatch,
    },
}: TermFilterCheckboxMenuProps<T>): ReactElement => {
    const [isOpen, setIsOpen] = useState<boolean>(false);
    const toggleRef = useRef<HTMLButtonElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    const selectedItems: string[] =
        (filterStates?.[field] as TermsFilterState)?.include ?? [];

    const handleMenuKeys = (event: KeyboardEvent) => {
        if (isOpen && menuRef.current?.contains(event.target as Node)) {
            if (event.key === "Escape" || event.key === "Tab") {
                setIsOpen(!isOpen);
                toggleRef.current?.focus();
            }
        }
    };

    const handleClickOutside = (event: MouseEvent) => {
        if (isOpen && !menuRef.current?.contains(event.target as Node)) {
            setIsOpen(false);
        }
    };

    useEffect(() => {
        window.addEventListener("keydown", handleMenuKeys);
        window.addEventListener("click", handleClickOutside);
        return () => {
            window.removeEventListener("keydown", handleMenuKeys);
            window.removeEventListener("click", handleClickOutside);
        };
    }, [isOpen, menuRef]);

    const onToggleClick = (ev: React.MouseEvent) => {
        ev.stopPropagation();
        setTimeout(() => {
            if (menuRef.current) {
                const firstElement = menuRef.current.querySelector(
                    "li > button:not(:disabled)"
                );
                firstElement && (firstElement as HTMLElement).focus();
            }
        }, 0);
        setIsOpen(!isOpen);
    };

    function onSelect(
        _event: React.MouseEvent | undefined,
        itemId: string | number | undefined
    ) {
        if (typeof itemId === "undefined") {
            return;
        }

        const itemIdStr = itemId.toString();
        if (selectedItems.includes(itemIdStr)) {
            dispatch({ type: "toggleTerm", field, bucketKey: itemIdStr });
        } else {
            dispatch({ type: "toggleTerm", field, bucketKey: itemIdStr });
        }
    }

    const filterConfig = filter!.find(
        (f) => f.field === field
    )! as TermsFilterConfig;
    const buckets = (aggregations?.[field]?.buckets || []) as EsTermsBucket[];

    return (
        <Popper
            triggerRef={toggleRef}
            trigger={
                <MenuToggle
                    ref={toggleRef}
                    onClick={onToggleClick}
                    isExpanded={isOpen}
                    icon={<FilterIcon />}
                    {...(selectedItems.length > 0 && {
                        badge: (
                            <Badge isRead={false}>{selectedItems.length}</Badge>
                        ),
                    })}
                >
                    Filter placeholder
                </MenuToggle>
            }
            popperRef={menuRef}
            popper={
                <Menu
                    ref={menuRef}
                    id="checkbox-select-menu"
                    onSelect={onSelect}
                    selected={selectedItems}
                    role="listbox"
                >
                    <MenuContent>
                        <MenuList>
                            {(filterConfig.orderBucketBy
                                ? buckets.sort(filterConfig.orderBucketBy)
                                : buckets.sort(
                                      (a, b) => b.doc_count - a.doc_count
                                  )
                            ).map((bucket) => (
                                <MenuItem
                                    key={bucket.key}
                                    isSelected={selectedItems.includes(
                                        bucket.key.toString()
                                    )}
                                    itemId={bucket.key}
                                >
                                    <Split hasGutter>
                                        <SplitItem isFilled>
                                            {bucket.key}
                                        </SplitItem>
                                        <SplitItem>
                                            <Badge
                                                isRead={
                                                    !selectedItems.includes(
                                                        bucket.key.toString()
                                                    )
                                                }
                                            >
                                                {bucket.doc_count}
                                            </Badge>
                                        </SplitItem>
                                    </Split>
                                </MenuItem>
                            ))}
                        </MenuList>
                    </MenuContent>
                </Menu>
            }
            isVisible={isOpen}
        />
    );
};

export default TermFilterCheckboxMenu;
