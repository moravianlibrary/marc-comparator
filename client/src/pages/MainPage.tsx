import { useEffect, useState, type ReactElement } from "react";
import "@patternfly/react-core/dist/styles/base.css";

import { Routes, Route, useNavigate, useLocation } from "react-router";
import {
    Page,
    Masthead,
    PageSidebar,
    Nav,
    NavList,
    NavItem,
    MastheadMain,
    MastheadToggle,
    PageToggleButton,
    MastheadContent,
    PageSidebarBody,
    NavExpandable,
    PageSection,
    NavGroup,
} from "@patternfly/react-core";
import { useTranslation } from "react-i18next";
import RecordsTable from "./RecordsTable";
import RecordsDashboardSection from "./RecordsDashboardSection";
import RecordDetailsSection from "./RecordDetailsSection";
import SystemSettingsSection from "./SystemSettingsSection";
import SystemMaintenance from "./SystemMaintenance";
import RecordsAddition from "./RecordsAddition";

interface NavigationItem {
    key: string;
    to: string;
}

interface NavigationSection {
    section: string;
    items: NavigationItem[];
}

const NAVIGATION_CONFIG: (NavigationSection | NavigationItem)[] = [
    { key: "home", to: "/" },
    {
        section: "records",
        items: [
            { key: "table", to: "/records/table" },
            { key: "dashboard", to: "/records/dashboard" },
            { key: "details", to: "/records/details" },
            { key: "addition", to: "/records/addition" },
        ],
    },
    {
        section: "tasks",
        items: [
            { key: "overview", to: "/tasks" },
            { key: "settings", to: "/tasks/settings" },
        ],
    },
    {
        section: "record-tools",
        items: [
            { key: "authority-linkers", to: "/record-tools/authority-linkers" },
            { key: "comparators", to: "/record-tools/comparators" },
            { key: "validators", to: "/record-tools/validators" },
        ],
    },
    {
        section: "administration",
        items: [
            { key: "access-control", to: "/administration/access-control" },
            { key: "system-settings", to: "/administration/system-settings" },
            {
                key: "system-maintenance",
                to: "/administration/system-maintenance",
            },
        ],
    },
];

interface NavigationItemReverse extends NavigationItem {
    section: string;
}

const NAVIGATION_ITEMS: NavigationItemReverse[] = NAVIGATION_CONFIG.flatMap(
    (section) =>
        "items" in section
            ? section.items.map((item) => ({
                  ...item,
                  section: section.section,
              }))
            : [{ ...section, section: "n/a" }]
).filter((item) => item.key !== "home");

interface NavOnSelectProps {
    groupId: number | string;
    itemId: number | string;
    to: string;
}

const MainPage = (): ReactElement => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();

    const initItem = NAVIGATION_ITEMS.filter((item) =>
        location.pathname.startsWith(item.to)
    ).sort((a, b) => b.to.length - a.to.length)[0];

    const [activeGroup, setActiveGroup] = useState<string>(
        initItem?.section || "n/a"
    );
    const [activeItem, setActiveItem] = useState<string>(
        initItem?.key || "home"
    );

    useEffect(() => {
        const currentItem = NAVIGATION_ITEMS.filter((item) =>
            location.pathname.startsWith(item.to)
        ).sort((a, b) => b.to.length - a.to.length)[0];
        if (currentItem) {
            setActiveItem(currentItem.key);
            setActiveGroup(currentItem.section);
        }
    }, [location.pathname]);

    const onNavSelect = (
        _event: React.FormEvent<HTMLInputElement>,
        selectedItem: NavOnSelectProps
    ) => {
        _event.preventDefault();
        setActiveItem(selectedItem.itemId as string);
        navigate(selectedItem.to);
    };

    const masthead = (
        <Masthead>
            <MastheadMain>
                <MastheadToggle>
                    <PageToggleButton
                        isHamburgerButton
                        aria-label="Global navigation"
                    />
                </MastheadToggle>
                {/* <MastheadBrand>
                    <MastheadLogo>
                        <Brand
                            src={pfLogo}
                            alt="PatternFly"
                            heights={{ default: "36px" }}
                        />
                    </MastheadLogo>
                </MastheadBrand> */}
            </MastheadMain>
            <MastheadContent>
                <a>Content</a>
            </MastheadContent>
        </Masthead>
    );

    const navItem = (item: NavigationItem, section?: string) => {
        return (
            <NavItem
                key={item.key}
                itemId={item.key}
                to={item.to}
                isActive={activeItem === item.key}
            >
                {section
                    ? t(`navbar:${section}.${item.key}`)
                    : t(`navbar:${item.key}`)}
            </NavItem>
        );
    };

    const navSection = (section: NavigationSection) => {
        return (
            <NavGroup
                key={section.section}
                title={t(`navbar:${section.section}.section-title`)}
            >
                {section.items.map((item) => navItem(item, section.section))}
            </NavGroup>
        );
    };

    // TODO: This is compact version of sidebar, make also expanded version and toggle between them
    // Expanded version should have Sections instead of Expandables
    const pageNav = (
        <Nav onSelect={onNavSelect}>
            <NavList>
                {NAVIGATION_CONFIG.map((entry) =>
                    "section" in entry ? navSection(entry) : navItem(entry)
                )}
            </NavList>
        </Nav>
    );

    const sidebar = (
        <PageSidebar>
            <PageSidebarBody>{pageNav}</PageSidebarBody>
        </PageSidebar>
    );

    return (
        <Page masthead={masthead} sidebar={sidebar} isManagedSidebar>
            <Routes>
                <Route path="/records/table" element={<RecordsTable />} />
                <Route
                    path="/records/dashboard"
                    element={<RecordsDashboardSection />}
                />
                <Route
                    path="/records/details"
                    element={<RecordDetailsSection />}
                />
                <Route path="/records/addition" element={<RecordsAddition />} />
                <Route
                    path="/administration/system-settings"
                    element={<SystemSettingsSection />}
                />
                <Route
                    path="/administration/system-maintenance"
                    element={<SystemMaintenance />}
                />
            </Routes>
        </Page>
    );
};

export default MainPage;
