import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "/calls", label: "Live Calls", icon: "☏" },
  { to: "/voice", label: "Voice Lab", icon: "♪" },
  { to: "/integrations", label: "DishHome Integration", icon: "⚙" },
  { to: "/settings", label: "Settings", icon: "⚒" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-dishhome-mist">
      <aside className="w-64 bg-dishhome-blue text-white flex flex-col">
        <Link to="/" className="px-6 py-5 flex items-center gap-3 border-b border-white/10">
          <span className="inline-block w-3 h-3 rounded-full bg-dishhome-orange" />
          <div className="leading-tight">
            <div className="font-semibold">DishHome AI</div>
            <div className="text-[11px] uppercase tracking-widest text-white/60">
              Call Center
            </div>
          </div>
        </Link>

        <nav className="flex-1 py-4">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-2.5 text-sm transition ${
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
    </div>
  );
}
