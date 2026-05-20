import { useEffect, useMemo, useState, type ReactElement } from "react";
import { useNavigate, useLocation } from "react-router";
import { Nav, NavList, NavItem, NavGroup } from "@patternfly/react-core";
import { useTranslation } from "react-i18next";
import type { Me } from "../models/api/responses/users";
import { appSections } from "../app/appSections";
import {
    flattenMenuForNav,
    joinMenuPaths,
} from "../app/appMenu.utils";
import type { AppMenuEntry } from "../app/appMenu.types";
import type { UserGuard } from "../app/userGuards";

function getActiveItemId(
    pathname: string,
    flat: { path: string; itemId: string }[]
): string {
    const exact = flat.find(
        ({ path }) => pathname === path || pathname.startsWith(path + "?")
    );
    if (exact) return exact.itemId;
    const byPrefix = flat.find(
        ({ path }) =>
            path !== "/" &&
            (pathname === path || pathname.startsWith(path + "/"))
    );
    if (byPrefix) return byPrefix.itemId;
    return flat[0]?.itemId ?? "home";
}

export default function AppNavigation({
    user,
}: {
    user: Me | null | undefined;
}): ReactElement {
    const { t } = useTranslation("navbar");
    const navigate = useNavigate();
    const location = useLocation();
    const flat = useMemo(() => flattenMenuForNav(appSections), []);
    const [activeItem, setActiveItem] = useState<string>("home");

    useEffect(() => {
        setActiveItem(getActiveItemId(location.pathname, flat));
    }, [location.pathname, flat]);

    const onNavSelect = (
        event: React.FormEvent<HTMLInputElement>,
        { itemId, to }: { itemId: string | number; to: string }
    ) => {
        event.preventDefault();
        setActiveItem(String(itemId));
        navigate(to);
    };

    const isAllowed = (guard: UserGuard | null, u: Me | null | undefined) => {
        if (guard == null) return true;
        return guard(u);
    };

    const renderSection = (entry: AppMenuEntry): ReactElement => {
        if (entry.type === "section") {
            const to = entry.path;
            const itemId = entry.id;
            if (!isAllowed(entry.guard, user)) return <></>;

            return (
                <NavItem
                    key={itemId}
                    itemId={String(itemId)}
                    to={to}
                    isActive={activeItem === itemId}
                >
                    {t(itemId)}
                </NavItem>
            );
        }

        const group = entry;

        const visibleChildren = group.children.filter((child) => {
            const effectiveGuard = child.guard ?? group.guard;
            return isAllowed(effectiveGuard, user);
        });

        if (visibleChildren.length === 0) return <></>;

        return (
            <NavGroup title={t(`${group.id}.group-title`)} key={String(group.id)}>
                {visibleChildren.map((child) => {
                    const effectiveGuard = child.guard ?? group.guard;
                    // Already filtered above, but keep local for type clarity.
                    if (!isAllowed(effectiveGuard, user)) return null;

                    const to = joinMenuPaths(group.prefix, child.path);
                    const itemId = `${group.id}.${child.id}`;
                    return (
                        <NavItem
                            key={itemId}
                            itemId={itemId}
                            to={to}
                            isActive={activeItem === itemId}
                        >
                            {t(itemId)}
                        </NavItem>
                    );
                })}
            </NavGroup>
        );
    };

    return (
        <Nav onSelect={onNavSelect}>
            <NavList>{appSections.map(renderSection)}</NavList>
        </Nav>
    );
}
