import {
    Button,
    EmptyState,
    EmptyStateBody,
    EmptyStateFooter,
    EmptyStateActions,
} from "@patternfly/react-core";
import SearchIcon from "@patternfly/react-icons/dist/esm/icons/search-icon";
import type { StaticUiText } from "../../models/ui/text";

export interface NoMatchFoundStateTexts {
    title: StaticUiText;
    body: StaticUiText;
    clearFilters?: StaticUiText;
}

interface NoMatchFoundStateProps {
    onClearFilters?: () => void;
    texts: NoMatchFoundStateTexts;
}

const NoMatchFoundState = ({
    onClearFilters,
    texts: { title, body, clearFilters },
}: NoMatchFoundStateProps) => {
    return (
        <EmptyState titleText={title} headingLevel="h4" icon={SearchIcon}>
            <EmptyStateBody>{body}</EmptyStateBody>
            {onClearFilters && (
                <EmptyStateFooter>
                    <EmptyStateActions>
                        <Button variant="link" onClick={onClearFilters}>
                            {clearFilters}
                        </Button>
                    </EmptyStateActions>
                </EmptyStateFooter>
            )}
        </EmptyState>
    );
};

export default NoMatchFoundState;
