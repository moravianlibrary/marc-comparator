import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import WithProviders from "./components/atoms/WithProviders.tsx";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./services/queryClient.ts";
import { makeServer } from "./mocks/server.ts";
import NotificationProvider from "./hooks/useNotifications.tsx";
import "./services/locales.ts";

const DISABLE_MOCKS = true;

if (import.meta.env.DEV && !DISABLE_MOCKS) {
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
                NotificationProvider,
            ]}
        >
            <App />
        </WithProviders>
    </StrictMode>
);
