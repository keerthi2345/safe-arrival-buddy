import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import PublicShell from "../components/PublicShell.jsx";
import StatusBadge from "../components/StatusBadge";
import { formatDateTime } from "../utils";

const POLL_MS = 5000;

export default function WatchPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await api.getWatch(token);
        if (!cancelled) {
          setData(result);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e.status === 404 ? "This link is not valid." : e.message);
      }
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token]);

  async function acknowledge() {
    setBusy(true);
    try {
      setData(await api.ackWatch(token));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!data && error) {
    return (
      <PublicShell>
        <div className="card">
          <p className="error" style={{ margin: 0 }}>{error}</p>
        </div>
      </PublicShell>
    );
  }
  if (!data) {
    return (
      <PublicShell>
        <p className="muted">Loading…</p>
      </PublicShell>
    );
  }

  const name = data.traveller_name;
  const headlines = {
    active: { text: `${name}'s trip is in progress`, sub: "Nothing is needed from you right now.", tone: "info", icon: "→" },
    alerted: { text: `${name} has not checked in`, sub: "Please try to contact them.", tone: "alert", icon: "!" },
    safe: { text: `${name} is safe`, sub: "They have confirmed they arrived.", tone: "ok", icon: "✓" },
    resolved: { text: `${name}'s trip is resolved`, sub: "No further action is needed.", tone: "ok", icon: "✓" },
  };
  const h = headlines[data.status] || { text: data.status, sub: "", tone: "info", icon: "i" };

  return (
    <PublicShell>
      <div className="card">
        <div className={`hero hero-${h.tone}`}>
          <div className="hero-icon">{h.icon}</div>
          <div>
            <h2>{h.text}</h2>
            <p>{h.sub}</p>
          </div>
        </div>

        <div className="card-head">
          <h3>{data.label || "Trip"}</h3>
          <StatusBadge status={data.status} />
        </div>

        <dl className="facts">
          <div>
            <dt>Expected by</dt>
            <dd>{formatDateTime(data.deadline)}</dd>
          </div>
          {data.alerted_at && (
            <div>
              <dt>Alert sent</dt>
              <dd>{formatDateTime(data.alerted_at)}</dd>
            </div>
          )}
          {data.safe_at && (
            <div>
              <dt>Marked safe</dt>
              <dd>{formatDateTime(data.safe_at)}</dd>
            </div>
          )}
        </dl>
        {data.note && <p className="muted">Note from {name}: {data.note}</p>}

        {data.status === "alerted" && !data.acknowledged && (
          <button className="btn block" onClick={acknowledge} disabled={busy}>
            {busy ? "Saving…" : "I've seen this"}
          </button>
        )}
        {data.status === "alerted" && data.acknowledged && (
          <p className="banner banner-info" style={{ marginBottom: 0 }}>
            Thanks, you've confirmed you've seen this. Please try to contact {name}.
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </div>
      <p className="muted" style={{ textAlign: "center" }}>This page updates by itself every few seconds.</p>
    </PublicShell>
  );
}