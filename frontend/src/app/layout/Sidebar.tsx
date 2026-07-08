import { NavLink } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/experiments", label: "Experiments" },
  { to: "/compare", label: "Compare" },
  { to: "/events", label: "Events" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  const auth = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-title">Trading Lab</div>
      <nav className="nav-list" aria-label="Primary navigation">
        {links.map((link) => (
          <NavLink
            key={link.to}
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
            to={link.to}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      {auth.authEnabled && (
        <div className="sidebar-auth">
          <span>{auth.username ?? "Signed in"}</span>
          <button type="button" onClick={auth.logout}>
            Logout
          </button>
        </div>
      )}
    </aside>
  );
}
