import { createBrowserRouter, Navigate } from "react-router-dom";

import { App } from "../app/App";
import { CreateExperimentPage } from "../pages/CreateExperimentPage";
import { DashboardPage } from "../pages/DashboardPage";
import { ExperimentDetailPage } from "../pages/ExperimentDetailPage";
import { ExperimentsPage } from "../pages/ExperimentsPage";
import { SettingsPage } from "../pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "experiments", element: <ExperimentsPage /> },
      { path: "experiments/new", element: <CreateExperimentPage /> },
      { path: "experiments/:experimentId", element: <ExperimentDetailPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
