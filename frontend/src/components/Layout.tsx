import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { DishHomeLogo } from "./Logo";
import KhushiChatbot from "./KhushiChatbot";
import { useTheme } from "./ThemeProvider";

import {
  LayoutDashboard,
  Phone,
  Inbox,
  Users,
  Contact,
  Settings,
  Mic,
  HelpCircle,
  Send,
  MessageSquareReply,
  Shield,
  Activity,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  requires?: string; // permission required to see this link
}

interface NavGroup {
  title: string;
  items: NavItem[];
  requires?: string;
}

const NAV: NavGroup[] = [
  {
    title: "Operations",
    items: [
      { to: "/", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
      { to: "/calls", label: "Live Calls", icon: <Phone size={18} />, requires: "calls.read" },
      { to: "/inbox", label: "Inbox", icon: <Inbox size={18} />, requires: "inbox.read" },
    ],
  },
  {
    title: "Customers",
    items: [
      { to: "/customers", label: "Demo Customers", icon: <Users size={18} />, requires: "customers.read" },
      { to: "/contacts", label: "Contacts", icon: <Contact size={18} />, requires: "contacts.read" },
      { to: "/integrations", label: "DishHome System", icon: <Settings size={18} /> },
    ],
  },
  {
    title: "AI",
    items: [
      { to: "/voice", label: "Voice Lab", icon: <Mic size={18} />, requires: "voice.read" },
      { to: "/faqs", label: "FAQs", icon: <HelpCircle size={18} />, requires: "faqs.read" },
      { to: "/campaigns", label: "Campaigns", icon: <Send size={18} />, requires: "campaigns.read" },
      { to: "/saved-replies", label: "Saved Replies", icon: <MessageSquareReply size={18} />, requires: "inbox.read" },
    ],
  },
  {
    title: "Admin",
    requires: "users.manage",
    items: [
      { to: "/admin/access", label: "Access Portal", icon: <Shield size={18} />, requires: "users.manage" },
      { to: "/admin/login-activity", label: "Login Activity", icon: <Activity size={18} />, requires: "users.manage" },
      { to: "/settings", label: "Settings", icon: <Settings size={18} /> },
    ],
  },
];

function hasPerm(perms: string[] | undefined, required: string | undefined): boolean {
  if (!required) return true;
  return !!perms?.includes(required);
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const perms = user?.permissions ?? [];

  const visibleGroups = NAV
    .filter((g) => hasPerm(perms, g.requires))
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => hasPerm(perms, i.requires)),
    }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="min-h-screen flex bg-dishhome-mist dark:bg-dishhome-ink text-dishhome-ink dark:text-dishhome-mist">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-dishhome-blue text-white flex flex-col transform transition-transform duration-300 md:relative md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-5 py-5 flex items-center justify-between border-b border-white/10">
          <Link to="/" onClick={() => setSidebarOpen(false)}>
            <DishHomeLogo />
          </Link>
          <button className="md:hidden" onClick={() => setSidebarOpen(false)}>
            <X size={20} className="text-white/70" />
          </button>
        </div>

        <nav className="flex-1 py-4 overflow-y-auto">
          {visibleGroups.map((group) => (
            <div key={group.title} className="mb-4">
              <div className="px-6 mb-1.5 text-[10px] uppercase tracking-widest text-white/40 font-semibold">
                {group.title}
              </div>
              {group.items.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.to === "/"}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-6 py-2 text-sm transition ${
                      isActive
                        ? "bg-white/10 border-l-2 border-dishhome-orange text-white"
                        : "border-l-2 border-transparent text-white/75 hover:bg-white/5 hover:text-white"
                    }`
                  }
                >
                  <span className="w-5 flex justify-center text-white/60">{n.icon}</span>
                  {n.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-white/10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs text-white/60 uppercase tracking-widest mb-1">
                Signed in
              </div>
              <div className="text-sm font-medium">{user?.name}</div>
              <div className="text-xs text-white/60">{user?.role}</div>
            </div>
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="p-2 rounded-full hover:bg-white/10 text-white/70 hover:text-white transition"
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="w-full flex items-center justify-center gap-2 text-xs uppercase tracking-widest text-white/70 hover:text-white border border-white/20 hover:border-white/40 rounded-md py-1.5 transition"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white dark:bg-dishhome-ink border-b border-black/5 dark:border-white/5">
          <Link to="/">
            <DishHomeLogo variant={theme === "dark" ? "dark" : "light"} />
          </Link>
          <button onClick={() => setSidebarOpen(true)}>
            <Menu size={24} className="text-dishhome-blue dark:text-dishhome-mist" />
          </button>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      {/* Khushi AI Chatbot — floating widget on all pages */}
      <KhushiChatbot />
    </div>
  );
}
