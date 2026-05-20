import type { ReactNode, FC, ComponentType } from "react";

interface WithProvidersProps {
    providers: ComponentType<{ children: ReactNode }>[];
    children: ReactNode;
}

const WithProviders: FC<WithProvidersProps> = ({ providers, children }) => {
    return providers.reduceRight(
        (acc, Provider) => <Provider>{acc}</Provider>,
        children
    );
};

export default WithProviders;
