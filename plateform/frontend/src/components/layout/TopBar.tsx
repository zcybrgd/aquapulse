import { Bell, Menu } from "lucide-react";

import { operatingZones } from "../../data/zones";
import { StatusDot } from "../ui/StatusDot";

interface TopBarProps {
  title: string;
  onOpenSidebar: () => void;
}

export function TopBar({ title, onOpenSidebar }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-[var(--topbar-height)] items-center gap-3 border-b border-line bg-white/95 px-4 backdrop-blur-sm sm:px-6">
      <button
        type="button"
        className="rounded-xl p-2 text-ink hover:bg-page lg:hidden"
        onClick={onOpenSidebar}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-ink">{title}</h1>
      </div>

      <label className="sr-only" htmlFor="zone-selector">
        Operating zone
      </label>
      <select
        id="zone-selector"
        className="hidden h-10 max-w-[11rem] truncate rounded-xl border border-line bg-white px-3 text-sm text-ink sm:block"
        defaultValue="all"
      >
        {operatingZones.map((zone) => (
          <option key={zone.id} value={zone.id}>
            {zone.label}
          </option>
        ))}
      </select>

      <div className="hidden items-center rounded-xl border border-line bg-page px-3 py-2 md:flex">
        <StatusDot label="Waiting for integration" />
      </div>

      <button
        type="button"
        className="relative rounded-xl p-2 text-ink-muted hover:bg-page hover:text-ink"
        aria-label="Notifications"
      >
        <Bell size={18} />
        <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-teal" />
      </button>

      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-light text-xs font-semibold text-navy"
        aria-label="Operator"
        title="Operator"
      >
        OP
      </div>
    </header>
  );
}
