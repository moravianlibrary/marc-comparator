import { useQuery } from '@tanstack/react-query';
import { type CSSProperties, useEffect, useLayoutEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Skeleton } from '@/components/ui/skeleton';
import { useGetMe } from '@/hooks/use-auth';
import { useWsEvents } from '@/hooks/use-ws-events';
import apiClient from '@/lib/api-client';
import { LockBanner } from './lock-banner';
import { MainBanner } from './main-banner';

export function AppLayout() {
  const { isLoading: isHealthLoading, isError: isHealthError } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.get('/system/health'),
    retry: 1,
  });

  const { data: me, isLoading: isMeLoading, isError: isMeError } = useGetMe();
  useWsEvents();

  // The shell owns the banners, so the shell is what can say how much room is
  // left under them. It publishes that as a custom property instead of each
  // page measuring the layout from the outside: a page that walks up to
  // `main` and guesses at its siblings breaks silently the day the shell
  // changes shape. The banners appear, disappear and wrap, hence the
  // observer rather than a one-off read, and a callback ref rather than
  // `useRef` — the banners sit behind the loading and redirect returns
  // below, so an effect keyed on mount alone would run while they are still
  // unrendered and never see them arrive.
  const [header, setHeader] = useState<HTMLDivElement | null>(null);
  const [headerHeight, setHeaderHeight] = useState(0);

  useLayoutEffect(() => {
    if (!header) {
      return;
    }

    const measure = () => setHeaderHeight(header.getBoundingClientRect().height);
    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(header);
    return () => observer.disconnect();
  }, [header]);

  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (isHealthError) {
      setRedirecting(true);
      const redirect = window.location.pathname + window.location.search;
      window.location.href = `/service-unavailable?redirect=${encodeURIComponent(redirect)}`;
    } else if (!isHealthLoading && !isMeLoading && (isMeError || !me)) {
      setRedirecting(true);
      const currentPath = window.location.pathname;
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
    }
  }, [isHealthError, isHealthLoading, isMeLoading, isMeError, me]);

  if (isHealthLoading || isMeLoading) {
    return (
      <div className="flex h-screen flex-col">
        {/* Banner skeleton */}
        <div className="flex h-14 items-center gap-4 border-b px-4">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-4 w-32" />
          <div className="flex-1" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
        {/* Content skeleton */}
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
          <div className="grid grid-cols-3 gap-4 pt-4">
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-48 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (redirecting || isHealthError || isMeError || !me) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col animate-fade-in">
      <div ref={setHeader} className="sticky top-0 z-50">
        <LockBanner />
        <MainBanner />
      </div>

      <main
        className="flex-1 p-6"
        // `p-6` is 1.5rem top and bottom; subtract both so a page asking for
        // the full content height does not overflow its own padding.
        style={
          {
            '--app-content-height': `calc(100dvh - ${headerHeight}px - 3rem)`,
          } as CSSProperties
        }
      >
        <Outlet />
      </main>
    </div>
  );
}
