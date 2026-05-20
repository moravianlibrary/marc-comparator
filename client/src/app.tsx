import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { NuqsAdapter } from "nuqs/adapters/react-router/v7";
import { Toaster } from "@/components/ui/sonner";
import { queryClient } from "@/lib/query-client";
import { router } from "@/router";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NuqsAdapter>
        <RouterProvider router={router} />
      </NuqsAdapter>
      <Toaster position="bottom-right" richColors />
    </QueryClientProvider>
  );
}
