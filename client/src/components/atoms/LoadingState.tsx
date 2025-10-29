import { EmptyState, Spinner } from "@patternfly/react-core";
import type { StaticUiText } from "../../models/ui/text";

interface LoadingStateProps {
    title: StaticUiText;
}

const LoadingState = ({ title }: LoadingStateProps) => {
    return <EmptyState titleText={title} headingLevel="h4" icon={Spinner} />;
};

export default LoadingState;
