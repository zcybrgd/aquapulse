import { NavLink } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";

import { primaryNav, utilityNav } from "../../data/navigation";
import { useMediaQuery } from "../../hooks/useMediaQuery";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

function NavGroup({
  items,
  onNavigate,
}: {
  items: typeof primaryNav;
  onNavigate: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <li key={item.path}>
            <NavLink
              to={item.path}
              end={item.path === "/"}
              onClick={onNavigate}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "text-white"
                    : "text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <motion.span
                      layoutId={reduceMotion ? undefined : "sidebar-active"}
                      className="absolute inset-0 rounded-xl bg-white/10"
                      transition={{ duration: reduceMotion ? 0 : 0.22, ease: "easeOut" }}
                    />
                  ) : null}
                  <Icon size={18} className="relative z-10 shrink-0" aria-hidden="true" />
                  <span className="relative z-10 truncate">{item.label}</span>
                </>
              )}
            </NavLink>
          </li>
        );
      })}
    </ul>
  );
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const revealed = open || isDesktop;

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-navy/40 lg:hidden ${open ? "block" : "hidden"}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        ref={(node) => {
          if (node) {
            node.inert = !revealed;
          }
        }}
        className={`fixed inset-y-0 left-0 z-40 flex w-[var(--sidebar-width)] max-w-[85vw] flex-col overflow-hidden border-r border-white/5 bg-navy text-white transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        } ${revealed ? "" : "pointer-events-none"}`}
        aria-label="Primary"
        aria-hidden={!revealed}
      >
        <div className="flex h-[var(--topbar-height)] items-center justify-between px-5">
          <div className="flex min-w-0 items-center gap-2.5">
            <img
              src="/aquapulse-logo.png"
              alt=""
              width={32}
              height={32}
              className="h-8 w-8 shrink-0 rounded-lg object-contain"
            />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-wide">AquaPulse</p>
              <p className="truncate text-[11px] text-white/50">Operations</p>
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg p-1.5 text-white/70 hover:bg-white/10 hover:text-white lg:hidden"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex min-h-0 flex-1 flex-col px-3 pb-4 pt-2">
          <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
            <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">
              Control
            </p>
            <NavGroup items={primaryNav} onNavigate={onClose} />
          </div>
          <div className="mt-4 border-t border-white/10 pt-3">
            <NavGroup items={utilityNav} onNavigate={onClose} />
          </div>
        </nav>
      </aside>
    </>
  );
}
