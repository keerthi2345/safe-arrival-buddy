import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { login, register } from "../features/authSlice";
import PublicShell from "../components/PublicShell.jsx";

export default function LoginPage() {
  const dispatch = useDispatch();
  const { token, status, error } = useSelector((s) => s.auth);
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", name: "", password: "" });

  if (token) return <Navigate to="/" replace />;

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function submit(e) {
    e.preventDefault();
    if (mode === "login") dispatch(login({ email: form.email, password: form.password }));
    else dispatch(register(form));
  }

  const isLogin = mode === "login";

  return (
    <PublicShell wide>
      <div className="auth-grid">
        <aside className="auth-aside">
          <h2>Get home safe. Let someone know, without being tracked.</h2>
          <ul>
            <li>Set a time you'll arrive by. No location tracking.</li>
            <li>Tap "I'm safe" when you get there.</li>
            <li>If you don't, your trusted buddies are emailed, one after another.</li>
          </ul>
        </aside>
        <form className="card" onSubmit={submit} style={{ margin: 0 }}>
          <h2>{isLogin ? "Welcome back" : "Create your account"}</h2>
          <p className="muted">{isLogin ? "Log in to manage your trips." : "It takes under a minute."}</p>
          <label className="field">
            Email
            <input type="email" value={form.email} onChange={set("email")} required />
          </label>
          {!isLogin && (
            <label className="field">
              Name
              <input value={form.name} onChange={set("name")} required />
            </label>
          )}
          <label className="field">
            Password
            <input type="password" value={form.password} onChange={set("password")} required />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="btn block" disabled={status === "loading"}>
            {status === "loading" ? "Please wait…" : isLogin ? "Log in" : "Register"}
          </button>
          <p className="muted" style={{ marginTop: 14, marginBottom: 0 }}>
            {isLogin ? "No account yet? " : "Already registered? "}
            <button type="button" className="link" onClick={() => setMode(isLogin ? "register" : "login")}>
              {isLogin ? "Create one" : "Log in"}
            </button>
          </p>
        </form>
      </div>
    </PublicShell>
  );
}