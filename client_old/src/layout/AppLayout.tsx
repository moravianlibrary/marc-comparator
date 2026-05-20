import { useEffect, type ReactElement } from "react";
import { useNavigate, useLocation } from "react-router";
import {
    Page,
    PageSidebar,
    PageSidebarBody,
    Bullseye,
    Spinner,
} from "@patternfly/react-core";
import MainPageMasthead from "../pages/main-page/Masthead";
import AppNotificationDrawer from "../pages/main-page/NotificationDrawer";
import AppNavigation from "./AppNavigation";
import AppLayoutRoutes from "./AppLayoutRoutes";
import AuthPage from "../pages/AuthPage";
import { useGetMe } from "../hooks/useAuth";
import { useNotification } from "../hooks/useNotifications";

export default function AppLayout(): ReactElement {
    const { data: me, isLoading } = useGetMe();
    const { drawerExpanded } = useNotification();
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        if (!me && !isLoading) {
            if (
                location.pathname !== "/login" &&
                location.pathname !== "/signup"
            ) {
                navigate(
                    "/login?redirect=" + encodeURIComponent(location.pathname)
                );
            } else {
                navigate("/login");
            }
        }
    }, [me, isLoading, location.pathname, navigate]);

    if (isLoading) {
        return (
            <div style={{ height: "100vh" }}>
                <Bullseye>
                    <Spinner size="xl" />
                </Bullseye>
            </div>
        );
    }

    if (!me) {
        return <AuthPage />;
    }

    return (
        <Page
            masthead={<MainPageMasthead />}
            sidebar={
                <PageSidebar>
                    <PageSidebarBody>
                        <AppNavigation user={me} />
                    </PageSidebarBody>
                </PageSidebar>
            }
            notificationDrawer={<AppNotificationDrawer />}
            isNotificationDrawerExpanded={drawerExpanded}
            isManagedSidebar
        >
            <AppLayoutRoutes user={me} />
        </Page>
    );
}
