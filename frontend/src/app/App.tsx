import { Outlet } from "react-router-dom";

import { AppLayout } from "./layout/AppLayout";

export function App() {
  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}
