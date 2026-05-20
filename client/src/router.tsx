import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/layout/app-layout";
import { LoginPage } from "@/features/auth/login-page";
import { SignupPage } from "@/features/auth/signup-page";
import { LogoutPage } from "@/features/auth/logout-page";
import { SettingsPage } from "@/features/settings/settings-page";
import { TasksPage } from "@/features/tasks/tasks-page";
import { AccessControlPage } from "@/features/access-control/access-control-page";
import { SystemPage } from "@/features/system/system-page";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/signup",
    element: <SignupPage />,
  },
  {
    path: "/logout",
    element: <LogoutPage />,
  },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        index: true,
        lazy: async () => {
          const { RecordsPage } = await import(
            "@/features/records/records-page"
          );
          return { Component: RecordsPage };
        },
      },
      {
        path: "tasks",
        element: <TasksPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
      {
        path: "access-control",
        element: <AccessControlPage />,
      },
      {
        path: "system",
        element: <SystemPage />,
      },
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
