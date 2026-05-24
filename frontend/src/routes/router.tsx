import { createBrowserRouter, Navigate } from "react-router-dom";

import { App } from "../app/App";
import { ComparePage } from "../pages/ComparePage";
import { CreateExperimentPage } from "../pages/CreateExperimentPage";
import { DashboardPage } from "../pages/DashboardPage";
import { EventsPage } from "../pages/EventsPage";
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
      { path: "compare", element: <ComparePage /> },
      { path: "events", element: <EventsPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);
