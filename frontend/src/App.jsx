import { Navigate, Route, Routes } from "react-router-dom";
import { useSelector } from "react-redux";
import LoginPage from "./pages/LoginPage.jsx";
import TripsPage from "./pages/TripsPage.jsx";
import WatchPage from "./pages/WatchPage.jsx";
import BuddiesPage from "./pages/BuddiesPage.jsx";
import ConfirmPage from "./pages/ConfirmPage.jsx";

function RequireAuth({ children }) {
  const token = useSelector((s) => s.auth.token);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Public pages (no login needed) */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/watch/:token" element={<WatchPage />} />
      <Route path="/confirm" element={<ConfirmPage />} />

      {/* Traveller pages (login required) */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <TripsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/buddies"
        element={
          <RequireAuth>
            <BuddiesPage />
          </RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}