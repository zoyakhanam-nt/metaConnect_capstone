import { NavLink, Routes, Route, useNavigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Connections from "./pages/Connections.jsx";
import MetadataExplorer from "./pages/MetadataExplorer.jsx";
import Login from "./pages/Login.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { isAuthenticated, logout } from "./auth.js";

export default function App() {
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app">
      <nav className="navbar">
        <span className="brand">MetaConnect</span>
        {isAuthenticated() && (
          <>
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/connections">Connections</NavLink>
            <NavLink to="/explorer">Metadata Explorer</NavLink>
            <button className="logout-btn" onClick={handleLogout}>Logout</button>
          </>
        )}
      </nav>

      <main className="content">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/connections" element={<ProtectedRoute><Connections /></ProtectedRoute>} />
          <Route path="/explorer" element={<ProtectedRoute><MetadataExplorer /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  );
}