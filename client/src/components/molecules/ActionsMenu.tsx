import { useRef, useState } from "react";
import {
    Menu,
    MenuContainer,
    MenuContent,
    MenuItem,
    MenuList,
    MenuToggle,
} from "@patternfly/react-core";
import type {
    ActionConfig,
    ActionItemConfig,
    ActionSectionConfig,
} from "../../models/ui/actions";

interface ActionsMenuProps {
    config: ActionConfig[];
    disabled?: boolean;
    label: string;
}

const ActionsMenu: React.FC<ActionsMenuProps> = ({
    config,
    disabled,
    label,
}) => {
    const menuRef = useRef<HTMLDivElement>(null);
    const toggleRef = useRef<HTMLButtonElement>(null);

    const [isOpen, setIsOpen] = useState<boolean>(false);

    const toggle = (
        <MenuToggle
            ref={toggleRef}
            onClick={() => setIsOpen(!isOpen)}
            isExpanded={isOpen}
            isDisabled={disabled}
        >
            {label}
        </MenuToggle>
    );

    const menuItem = (config: ActionItemConfig) => (
        <MenuItem
            key={config.label}
            description={config.icon}
            itemId={config.label}
            onClick={() => {
                setIsOpen(false);
                config.onClick();
            }}
        >
            {config.label}
        </MenuItem>
    );

    const menuSection = (config: ActionSectionConfig) => (
        <MenuItem
            key={config.label}
            description={config.icon}
            flyoutMenu={
                <Menu key={config.label} containsFlyout>
                    <MenuContent>
                        <MenuList>{config.actions.map(menuElement)}</MenuList>
                    </MenuContent>
                </Menu>
            }
            itemId={config.label}
        >
            {config.label}
        </MenuItem>
    );

    const menuElement = (config: ActionConfig) => {
        if ("actions" in config) {
            return menuSection(config);
        } else {
            return menuItem(config);
        }
    };

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
            onOpenChange={(isOpen) => setIsOpen(isOpen)}
            menu={menu}
            menuRef={menuRef}
            toggle={toggle}
            toggleRef={toggleRef}
        />
    );
};

export default ActionsMenu;
