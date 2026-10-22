import { Link, NavLink } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { logout } from "../features/authSlice";

export function Brand({ to }) {
  const inner = (
    <span className="brand">
      <span className="brand-mark">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" />
          <path d="M8.5 12.5l2.5 2.5 4.5-5" />
        </svg>
      </span>
      <span className="brand-text">Safe Arrival Buddy</span>
    </span>
  );
  return to ? (
    <Link to={to} className="brand-link">
      {inner}
    </Link>
  ) : (
    inner
  );
}

export default function Layout({ title, subtitle, actions, children }) {
  const dispatch = useDispatch();
  const email = useSelector((s) => s.auth.email);
  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Brand to="/" />
          <div className="nav-links">
            <NavLink to="/" end>
              Trips
            </NavLink>
            <NavLink to="/buddies">Buddies</NavLink>
          </div>
          <div className="nav-user">
            <span className="nav-email">{email}</span>
            <button className="btn secondary sm" onClick={() => dispatch(logout())}>
              Log out
            </button>
          </div>
        </div>
      </nav>
      <main className="page">
        <header className="page-head">
          <div>
            <h1>{title}</h1>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
        {children}
      </main>
    </>
  );
}