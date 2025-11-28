import {
    useEffect,
    useRef,
    useState,
    type Dispatch,
    type ReactElement,
} from "react";
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
    type LabelProps,
    Label,
} from "@patternfly/react-core";
import { FilterIcon } from "@patternfly/react-icons";
import type { EsTermsBucket } from "../../models/api/responses/es_aggregations";
import type { CollectionData } from "../../store/collection/domain";
import type {
    EsState,
    EsStateAction,
    EsTermsFilterConfig,
} from "../../store/es/domain";
import { selectTermsBuckets } from "../../store/es/selectors";

const TermFilterCheckboxMenu = <T,>({
    field,
    state,
    dispatch,
    data,
    bucketsOrdering,
    renderBucketLabel,
    placeholder,
    labelProps,
}: {
    field: string;
    data?: CollectionData<T>;
    state: EsState;
    dispatch: Dispatch<EsStateAction>;
    bucketsOrdering?: (a: EsTermsBucket, b: EsTermsBucket) => number;
    renderBucketLabel?: (bucket: EsTermsBucket) => React.ReactNode | null;
    placeholder?: string;
    labelProps?: (bucketKey: string) => LabelProps | null;
}): ReactElement | null => {
    const [isOpen, setIsOpen] = useState<boolean>(false);
    const toggleRef = useRef<HTMLButtonElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    const filterConfig = state.config.filters?.[field] as
        | EsTermsFilterConfig
        | undefined;
    if (!filterConfig) return null;

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

    const filterState = state.terms?.[field];
    const include = new Set(filterState?.include || []);

    const buckets = selectTermsBuckets(field, state, data, bucketsOrdering);

    function onSelect(
        _event: React.MouseEvent | undefined,
        itemId: string | number | undefined
    ) {
        if (typeof itemId === "undefined") {
            return;
        }

        const itemIdStr = itemId.toString();
        if (include.has(itemIdStr)) {
            dispatch({ type: "toggleTerm", field, bucketKey: itemIdStr });
        } else {
            dispatch({ type: "toggleTerm", field, bucketKey: itemIdStr });
        }
    }

    const renderLabel = (bucket: EsTermsBucket) => {
        const currLabelProps = labelProps && labelProps(bucket.key.toString());
        if (currLabelProps) {
            return <Label {...currLabelProps}>{bucket.key.toString()}</Label>;
        }

        return renderBucketLabel ? (
            renderBucketLabel(bucket)
        ) : (
            <>{bucket.key.toString()}</>
        );
    };

    return (
        <Popper
            triggerRef={toggleRef}
            trigger={
                <MenuToggle
                    ref={toggleRef}
                    onClick={onToggleClick}
                    isExpanded={isOpen}
                    icon={<FilterIcon />}
                    {...(include.size > 0 && {
                        badge: <Badge isRead={false}>{include.size}</Badge>,
                    })}
                >
                    {placeholder}
                </MenuToggle>
            }
            popperRef={menuRef}
            popper={
                <Menu
                    ref={menuRef}
                    id="checkbox-select-menu"
                    onSelect={onSelect}
                    selected={Array.from(include)}
                    role="listbox"
                >
                    <MenuContent>
                        <MenuList>
                            {buckets.map((bucket) => (
                                <MenuItem
                                    key={bucket.key}
                                    isSelected={include.has(
                                        bucket.key.toString()
                                    )}
                                    itemId={bucket.key}
                                >
                                    <Split hasGutter>
                                        <SplitItem isFilled>
                                            {renderLabel(bucket)}
                                        </SplitItem>
                                        <SplitItem>
                                            <Badge
                                                isRead={
                                                    !include.has(
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
