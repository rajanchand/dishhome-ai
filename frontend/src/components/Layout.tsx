import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { DishHomeLogo } from "./Logo";
import KhushiChatbot from "./KhushiChatbot";

interface NavItem {
  to: string;
  label: string;
  icon: string;
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
      { to: "/", label: "Dashboard", icon: "▦" },
      { to: "/calls", label: "Live Calls", icon: "☏", requires: "calls.read" },
      { to: "/inbox", label: "Inbox", icon: "✉", requires: "inbox.read" },
    ],
  },
  {
    title: "Customers",
    items: [
      { to: "/customers", label: "Demo Customers", icon: "👥", requires: "customers.read" },
      { to: "/contacts", label: "Contacts", icon: "♟", requires: "contacts.read" },
      { to: "/integrations", label: "DishHome System", icon: "⚙" },
    ],
  },
  {
    title: "AI",
    items: [
      { to: "/voice", label: "Voice Lab", icon: "♪", requires: "voice.read" },
      { to: "/faqs", label: "FAQs", icon: "?", requires: "faqs.read" },
      { to: "/campaigns", label: "Campaigns", icon: "✈", requires: "campaigns.read" },
      { to: "/saved-replies", label: "Saved Replies", icon: "↪", requires: "inbox.read" },
    ],
  },
  {
    title: "Admin",
    requires: "users.manage",
    items: [
      { to: "/admin/access", label: "Access Portal", icon: "🛡", requires: "users.manage" },
      { to: "/admin/login-activity", label: "Login Activity", icon: "📍", requires: "users.manage" },
      { to: "/settings", label: "Settings", icon: "⚒" },
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
  const perms = user?.permissions ?? [];

  const visibleGroups = NAV
    .filter((g) => hasPerm(perms, g.requires))
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => hasPerm(perms, i.requires)),
    }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="min-h-screen flex bg-dishhome-mist">
      <aside className="w-64 bg-dishhome-blue text-white flex flex-col">
        <Link
          to="/"
          className="px-5 py-5 flex items-center border-b border-white/10"
        >
          <DishHomeLogo />
        </Link>

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
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-6 py-2 text-sm transition ${
                      isActive
                        ? "bg-white/10 border-l-2 border-dishhome-orange text-white"
                        : "border-l-2 border-transparent text-white/75 hover:bg-white/5 hover:text-white"
                    }`
                  }
                >
                  <span className="w-4 text-center text-white/60">{n.icon}</span>
                  {n.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-white/10">
          <div className="text-xs text-white/60 uppercase tracking-widest mb-1">
            Signed in
          </div>
          <div className="text-sm font-medium">{user?.name}</div>
          <div className="text-xs text-white/60">{user?.role}</div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="mt-3 w-full text-xs uppercase tracking-widest text-white/70 hover:text-white border border-white/20 hover:border-white/40 rounded-md py-1.5 transition"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Outlet />
      </main>

      {/* Khushi AI Chatbot — floating widget on all pages */}
      <KhushiChatbot />
    </div>
  );
}
