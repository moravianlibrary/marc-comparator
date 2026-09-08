import { QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7';
import { RouterProvider } from 'react-router-dom';
import { ApiErrorListener } from '@/components/api-error-listener';
import { Toaster } from '@/components/ui/sonner';
import { queryClient } from '@/lib/query-client';
import { router } from '@/router';

export function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        <NuqsAdapter>
          <RouterProvider router={router} />
        </NuqsAdapter>
        <Toaster position="top-center" richColors />
        <ApiErrorListener />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
