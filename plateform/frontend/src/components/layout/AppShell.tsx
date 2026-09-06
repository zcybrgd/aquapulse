import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { getPageTitle } from "../../data/navigation";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const title = getPageTitle(location.pathname);
  const isLiveMap = location.pathname === "/map";

  return (
    <div className="min-h-screen overflow-x-hidden bg-page">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="min-w-0 lg:pl-[var(--sidebar-width)]">
        <TopBar title={title} onOpenSidebar={() => setSidebarOpen(true)} />
        <main
          className={
            isLiveMap
              ? "h-[calc(100dvh-var(--topbar-height))] min-w-0 overflow-hidden p-0"
              : "min-w-0 overflow-x-hidden px-4 py-6 sm:px-6"
          }
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
