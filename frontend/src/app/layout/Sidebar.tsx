import { NavLink } from "react-router-dom";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/experiments", label: "Experiments" },
  { to: "/experiments/new", label: "Create" },
  { to: "/compare", label: "Compare" },
  { to: "/events", label: "Events" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
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
    </aside>
  );
}
