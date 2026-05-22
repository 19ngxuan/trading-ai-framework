import { ReactNode } from "react";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

type AppLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
