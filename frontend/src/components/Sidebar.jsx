import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "../auth.js";

export default function Sidebar() {
  const navigate = useNavigate();

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

      <button className="sidebar-logout" onClick={handleLogout}>
        Logout
      </button>
    </aside>
  );
}
