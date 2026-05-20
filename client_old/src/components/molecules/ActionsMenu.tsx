import { useRef, useState } from "react";
import {
    Dropdown,
    DropdownGroup,
    DropdownItem,
    DropdownList,
    Menu,
    MenuContainer,
    MenuContent,
    MenuItem,
    MenuList,
    MenuToggle,
    MenuToggleAction,
} from "@patternfly/react-core";
import { AngleDownIcon } from "@patternfly/react-icons";
import type {
    ActionConfig,
    ActionItemConfig,
    ActionSectionConfig,
} from "../../models/ui/actions";

interface ActionsMenuProps {
    config: ActionConfig[];
    disabled?: boolean;
    label?: string;
    icon?: React.ReactNode;
    mainAction?: ActionItemConfig;
    /** Section label shown above dropdown items when mainAction is set (e.g. "Advanced actions"). */
    dropdownSectionLabel?: string;
}

const ActionsMenu: React.FC<ActionsMenuProps> = ({
    config,
    disabled,
    label,
    icon,
    mainAction,
    dropdownSectionLabel,
}) => {
    const menuRef = useRef<HTMLDivElement>(null);
    const toggleRef = useRef<HTMLButtonElement>(null);
    const [isOpen, setIsOpen] = useState<boolean>(false);

    const menuItem = (item: ActionItemConfig) => (
        <MenuItem
            key={item.label}
            description={item.icon}
            itemId={item.label}
            onClick={() => {
                setIsOpen(false);
                item.onClick();
            }}
        >
            {item.label}
        </MenuItem>
    );

    const menuSection = (section: ActionSectionConfig) => (
        <MenuItem
            key={section.label}
            description={section.icon}
            flyoutMenu={
                <Menu key={section.label} containsFlyout>
                    <MenuContent>
                        <MenuList>{section.actions.map(menuElement)}</MenuList>
                    </MenuContent>
                </Menu>
            }
            itemId={section.label}
        >
            {section.label}
        </MenuItem>
    );

    const menuElement = (c: ActionConfig) => {
        if ("actions" in c) return menuSection(c);
        return menuItem(c);
    };

    if (mainAction != null) {
        const dropdownItems = config.flatMap(
            (c): Array<{ key: string; label: string; onClick: () => void }> =>
                "actions" in c
                    ? c.actions
                          .filter(
                              (a): a is ActionItemConfig => !("actions" in a),
                          )
                          .map((a) => ({
                              key: `${c.label}-${a.label}`,
                              label: a.label,
                              onClick: a.onClick,
                          }))
                    : [
                          {
                              key: c.label,
                              label: c.label,
                              onClick: (c as ActionItemConfig).onClick,
                          },
                      ],
        );
        return (
            <Dropdown
                isOpen={isOpen}
                onOpenChange={setIsOpen}
                onSelect={() => setIsOpen(false)}
                toggle={(toggleRef) => (
                    <MenuToggle
                        ref={toggleRef}
                        splitButtonItems={[
                            <MenuToggleAction
                                key="main-action"
                                isDisabled={disabled}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    mainAction.onClick();
                                }}
                            >
                                {mainAction.label}
                            </MenuToggleAction>,
                        ]}
                        onClick={() => setIsOpen(!isOpen)}
                        isExpanded={isOpen}
                        isDisabled={disabled}
                        icon={<AngleDownIcon />}
                        aria-label={label ?? mainAction.label}
                    />
                )}
            >
                {dropdownSectionLabel ? (
                    <DropdownGroup label={dropdownSectionLabel}>
                        <DropdownList>
                            {dropdownItems.map(
                                ({ key, label: itemLabel, onClick }) => (
                                    <DropdownItem
                                        key={key}
                                        onClick={() => {
                                            setIsOpen(false);
                                            onClick();
                                        }}
                                    >
                                        {itemLabel}
                                    </DropdownItem>
                                ),
                            )}
                        </DropdownList>
                    </DropdownGroup>
                ) : (
                    <DropdownList>
                        {dropdownItems.map(
                            ({ key, label: itemLabel, onClick }) => (
                                <DropdownItem
                                    key={key}
                                    onClick={() => {
                                        setIsOpen(false);
                                        onClick();
                                    }}
                                >
                                    {itemLabel}
                                </DropdownItem>
                            ),
                        )}
                    </DropdownList>
                )}
            </Dropdown>
        );
    }

    const toggle = (
        <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
            isDisabled={disabled}
            icon={icon}
        >
            {label}
        </MenuToggle>
    );

    const menu = (
        <Menu ref={menuRef} containsFlyout>
            <MenuContent>
                <MenuList>{config.map(menuElement)}</MenuList>
            </MenuContent>
        </Menu>
    );

    return (
        <MenuContainer
            isOpen={isOpen}
            onOpenChange={setIsOpen}
            menu={menu}
            menuRef={menuRef}
            toggle={toggle}
            toggleRef={toggleRef}
        />
    );
};

export default ActionsMenu;
