import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import WithProviders from "./components/atoms/WithProviders.tsx";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./services/queryClient.ts";
import { makeServer } from "./mocks/server.ts";
import { CatalogRecordsProvider } from "./hooks/useCatalogRecords.tsx";

if (import.meta.env.DEV) {
    makeServer();
}

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <WithProviders
            providers={[
                ({ children }) => (
                    <QueryClientProvider client={queryClient}>
                        {children}
                    </QueryClientProvider>
                ),
                CatalogRecordsProvider,
            ]}
        >
            <App />
        </WithProviders>
    </StrictMode>
);
