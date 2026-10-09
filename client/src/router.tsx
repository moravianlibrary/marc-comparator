import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AccessControlPage } from '@/features/access-control/access-control-page';
import { LoginPage } from '@/features/auth/login-page';
import { LogoutPage } from '@/features/auth/logout-page';
import { SignupPage } from '@/features/auth/signup-page';
import { ServiceUnavailablePage } from '@/features/errors/service-unavailable-page';
import { TasksPage } from '@/features/tasks/tasks-page';
import { AppLayout } from '@/layout/app-layout';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/service-unavailable',
    element: <ServiceUnavailablePage />,
  },
  {
    path: '/signup',
    element: <SignupPage />,
  },
  {
    path: '/logout',
    element: <LogoutPage />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        lazy: async () => {
          const { RecordsPage } = await import('@/features/records/records-page');
          return { Component: RecordsPage };
        },
      },
      {
        path: 'tasks',
        element: <TasksPage />,
      },
      {
        path: 'settings',
        lazy: async () => {
          const { SettingsPage } = await import('@/features/settings/settings-page');
          return { Component: SettingsPage };
        },
      },
      {
        path: 'periodic-sync',
        lazy: async () => {
          const { PeriodicSyncPage } = await import('@/features/settings/periodic-sync-page');
          return { Component: PeriodicSyncPage };
        },
      },
      {
        path: 'plugin-harvest',
        lazy: async () => {
          const { PluginHarvestPage } = await import('@/features/settings/plugin-harvest-page');
          return { Component: PluginHarvestPage };
        },
      },
      {
        path: 'access-control',
        element: <AccessControlPage />,
      },
      {
        path: 'maintenance',
        lazy: async () => {
          const { MaintenancePage } = await import('@/features/maintenance/maintenance-page');
          return { Component: MaintenancePage };
        },
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
