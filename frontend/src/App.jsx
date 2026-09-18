import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Services from "./pages/Services.jsx";
import MetadataExplorer from "./pages/MetadataExplorer.jsx";
import Login from "./pages/Login.jsx";
import ProtectedRoute from "./components/ProtectedRoutes.jsx";
import { AUTH_CHANGE_EVENT, isAuthenticated } from "./auth.js";

function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/services" element={<Services />} />
          <Route path="/explorer" element={<MetadataExplorer />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);

  useEffect(() => {
    const updateAuthentication = () => setAuthenticated(isAuthenticated());
    window.addEventListener(AUTH_CHANGE_EVENT, updateAuthentication);
    window.addEventListener("storage", updateAuthentication);
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, updateAuthentication);
      window.removeEventListener("storage", updateAuthentication);
    };
  }, []);

  return (
    <Routes>
      <Route
        path="/login"
        element={authenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/*"
        element={
          authenticated ? (
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}
