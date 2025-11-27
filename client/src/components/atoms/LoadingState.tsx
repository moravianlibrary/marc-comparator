import { Bullseye, EmptyState, Spinner } from "@patternfly/react-core";
import type { ReactNode } from "react";

interface LoadingStateProps {
    title?: ReactNode;
}

const LoadingState = ({ title }: LoadingStateProps) => {
    return (
        <Bullseye>
            <EmptyState titleText={title} headingLevel="h4" icon={Spinner} />
        </Bullseye>
    );
};

export default LoadingState;
