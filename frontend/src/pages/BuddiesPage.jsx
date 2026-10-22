import { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import Layout from "../components/Layout.jsx";
import { api } from "../api";

const MAX = 5;

export default function BuddiesPage() {
  const token = useSelector((s) => s.auth.token);
  const [buddies, setBuddies] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setBuddies(await api.listBuddies(token));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onAdd(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      await api.addBuddy(token, name.trim(), email.trim());
      setInfo(`Request emailed to ${email.trim()}. They must accept it before they can be alerted. Ask them to check spam.`);
      setName("");
      setEmail("");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onResend(id) {
    setError("");
    setInfo("");
    try {
      await api.resendBuddy(token, id);
      setInfo("Confirmation email sent again.");
    } catch (e) {
      setError(e.message);
    }
  }

  async function onRemove(id) {
    if (!window.confirm("Remove this buddy?")) return;
    setError("");
    setInfo("");
    try {
      await api.removeBuddy(token, id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  const accepted = buddies.filter((b) => b.status === "confirmed").length;
  const full = buddies.length >= MAX;

  return (
    <Layout
      title="My buddies"
      subtitle="Up to 5 people who are alerted one after another if you don't check in. Use a different email for each."
    >
      <div className="card">
        <div className="card-head">
          <h2 style={{ margin: 0 }}>
            {buddies.length} of {MAX} buddies
          </h2>
          <span className="muted">{accepted} accepted</span>
        </div>
        <div className="meter">
          <div style={{ width: `${(buddies.length / MAX) * 100}%` }} />
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          Buddy 1 is emailed first. If nobody taps "I've seen this" within 5 minutes, buddy 2 is emailed, and so on.
        </p>
      </div>

      <form className="card" onSubmit={onAdd}>
        <h2>Add a buddy</h2>
        <div className="row">
          <label className="field">
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} required disabled={full} />
          </label>
          <label className="field">
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required disabled={full} />
          </label>
        </div>
        {full && <p className="muted">You've reached 5 buddies. Remove one to add another.</p>}
        {error && <p className="error">{error}</p>}
        {info && <p className="banner banner-ok">{info}</p>}
        <button className="btn" disabled={busy || full} style={{ marginTop: info ? 12 : 0 }}>
          {busy ? "Sending…" : "Send request"}
        </button>
      </form>

      <div className="section-title">Alert order</div>
      {buddies.length === 0 && <div className="empty">No buddies yet. Add your first one above.</div>}
      {buddies.map((b) => (
        <div className="card" key={b.id}>
          <div className="buddy">
            <span className="order">{b.priority}</span>
            <div className="grow">
              <h3>{b.name}</h3>
              <p className="muted" style={{ margin: 0 }}>
                {b.email}
              </p>
            </div>
            <span className={`pill ${b.status === "confirmed" ? "pill-ok" : "pill-wait"}`}>
              {b.status === "confirmed" ? "Accepted" : "Waiting"}
            </span>
          </div>
          <div className="actions">
            {b.status === "pending" && (
              <button className="btn secondary sm" onClick={() => onResend(b.id)}>
                Resend email
              </button>
            )}
            <button className="btn danger sm" onClick={() => onRemove(b.id)}>
              Remove
            </button>
          </div>
        </div>
      ))}
    </Layout>
  );
}