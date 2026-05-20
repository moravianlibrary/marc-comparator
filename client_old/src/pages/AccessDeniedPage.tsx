import {
    Bullseye,
    EmptyState,
    EmptyStateBody,
    EmptyStateFooter,
    EmptyStateActions,
    Button,
    PageSection,
} from "@patternfly/react-core";
import { LockIcon } from "@patternfly/react-icons";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import type { ReactElement } from "react";

export default function AccessDeniedPage(): ReactElement {
    const { t } = useTranslation("auth");
    const navigate = useNavigate();

    return (
        <PageSection>
            <Bullseye>
                <EmptyState
                    titleText={t("access-denied.title")}
                    headingLevel="h4"
                    icon={LockIcon}
                >
                    <EmptyStateBody>{t("access-denied.body")}</EmptyStateBody>
                    <EmptyStateFooter>
                        <EmptyStateActions>
                            <Button variant="primary" onClick={() => navigate("/")}>
                                {t("access-denied.go-home")}
                            </Button>
                        </EmptyStateActions>
                    </EmptyStateFooter>
                </EmptyState>
            </Bullseye>
        </PageSection>
    );
}
