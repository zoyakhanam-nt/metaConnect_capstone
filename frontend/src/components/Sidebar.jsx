import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { getCurrentUser, logout } from "../auth.js";

export default function Sidebar() {
  const navigate = useNavigate();
  const [showUser, setShowUser] = useState(false);
  const user = getCurrentUser();
  const initial = (user.name || user.username || "U").charAt(0).toUpperCase();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="/favicon.svg" alt="MetaConnect" className="brand-mark" />
        <span>MetaConnect</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className="sidebar-link">
          Dashboard
        </NavLink>
        <NavLink to="/services" className="sidebar-link">
          Services
        </NavLink>
        <NavLink to="/explorer" className="sidebar-link">
          Explorer
        </NavLink>
      </nav>

      <div className="sidebar-user">
        {showUser && (
          <div className="user-popover">
            <strong>{user.name || user.username}</strong>
            <span>{user.email || user.username}</span>
          </div>
        )}
        <button
          className="user-trigger"
          title="View user information"
          onClick={() => setShowUser((visible) => !visible)}
        >
          <span className="user-avatar">{initial}</span>
          <span className="user-trigger-name">
            {user.name || user.username}
          </span>
        </button>
        <button className="sidebar-logout" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </aside>
  );
}
