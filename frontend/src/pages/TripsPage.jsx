import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { createTrip, extendTrip, fetchTrips, markSafe } from "../features/tripsSlice";
import Layout from "../components/Layout.jsx";
import StatusBadge from "../components/StatusBadge";
import { api } from "../api";
import { formatDateTime, parseUtc } from "../utils";

const POLL_MS = 10000;
const pad = (n) => String(n).padStart(2, "0");

function toLocalInput(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function TripForm() {
  const dispatch = useDispatch();
  const [form, setForm] = useState({ label: "", note: "", deadline: "", grace: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });
  const preset = (minutes) =>
    setForm({ ...form, deadline: toLocalInput(new Date(Date.now() + minutes * 60000)) });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const payload = {
      label: form.label,
      note: form.note,
      deadline: new Date(form.deadline).toISOString(),
    };
    if (form.grace) payload.grace_minutes = Number(form.grace);
    try {
      await dispatch(createTrip(payload)).unwrap();
      setForm({ label: "", note: "", deadline: "", grace: "" });
    } catch (err) {
      setError(typeof err === "string" ? err : "Could not create trip");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Start a trip</h2>
      <p className="muted">Pick when you expect to arrive. If you haven't checked in by then, your buddies are alerted.</p>
      <label className="field">
        Where are you going?
        <input value={form.label} onChange={set("label")} maxLength={100} placeholder="Home from college" />
      </label>
      <label className="field">
        Note for your buddy (optional)
        <input value={form.note} onChange={set("note")} maxLength={500} placeholder="Taking the 9:30 bus" />
      </label>
      <div className="row">
        <label className="field">
          I will arrive by
          <input type="datetime-local" value={form.deadline} onChange={set("deadline")} required />
        </label>
        <label className="field">
          Grace period (minutes)
          <input type="number" min="1" max="120" value={form.grace} onChange={set("grace")} placeholder="10" />
        </label>
      </div>
      <div className="chips">
        <span className="muted">Quick set:</span>
        {[30, 60, 120].map((m) => (
          <button type="button" className="chip" key={m} onClick={() => preset(m)}>
            in {m < 60 ? `${m} min` : `${m / 60} hr`}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      <button className="btn" disabled={busy}>
        {busy ? "Saving…" : "Start trip"}
      </button>
    </form>
  );
}

function Deliveries({ trip }) {
  const token = useSelector((s) => s.auth.token);
  const [rows, setRows] = useState(null);

  useEffect(() => {
    let off = false;
    async function load() {
      try {
        const r = await api.tripDeliveries(token, trip.id);
        if (!off) setRows(r);
      } catch {
        // keep the last known list
      }
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      off = true;
      clearInterval(id);
    };
  }, [token, trip.id]);

  if (!rows) return null;
  const sent = rows.filter((r) => r.status !== "no_buddies").sort((a, b) => a.level - b.level);

  if (sent.length === 0) {
    return (
      <p className="banner banner-warn">
        Nobody was alerted because you have no accepted buddies. <Link to="/buddies">Add a buddy</Link>, then tap
        "I'm safe".
      </p>
    );
  }
  const pill = (r) => {
    if (r.acknowledged_at) return <span className="pill pill-ok">Seen</span>;
    if (r.status === "failed") return <span className="pill pill-bad">Email failed</span>;
    if (r.status === "cancelled") return <span className="pill pill-wait">Cancelled</span>;
    return <span className="pill pill-wait">Emailed, waiting</span>;
  };
  return (
    <div>
      <p className="banner banner-alert">Your buddies are being alerted. Tap "I'm safe" when you are.</p>
      <ul className="deliveries">
        {sent.map((r) => (
          <li key={r.id}>
            <span className="order">{r.level}</span>
            <span className="grow">{r.buddy_email}</span>
            {pill(r)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TripCard({ trip }) {
  const dispatch = useDispatch();
  const token = useSelector((s) => s.auth.token);
  const [error, setError] = useState("");

  async function run(action) {
    setError("");
    try {
      await dispatch(action).unwrap();
    } catch (err) {
      setError(typeof err === "string" ? err : "Action failed");
    }
  }

  async function onDelete() {
    const warning =
      trip.status === "active" || trip.status === "alerted"
        ? "This trip is still open. Deleting it stops your buddies from watching it. Delete anyway?"
        : `Delete "${trip.label || "this trip"}"? This can't be undone.`;
    if (!window.confirm(warning)) return;
    setError("");
    try {
      await api.deleteTrip(token, trip.id);
      dispatch(fetchTrips());
    } catch (err) {
      setError(err.message);
    }
  }

  const deadline = parseUtc(trip.deadline);
  const alertAt = new Date(deadline.getTime() + trip.grace_minutes * 60000);
  const isActive = trip.status === "active";
  const isOpen = isActive || trip.status === "alerted";

  return (
    <div className={`card trip trip-${trip.status}`}>
      <div className="card-head">
        <h3>{trip.label || "Trip"}</h3>
        <StatusBadge status={trip.status} />
      </div>
      <p className="trip-meta">
        Arrive by {formatDateTime(trip.deadline)}
        {isActive && ` · buddy alerted at ${alertAt.toLocaleTimeString()}`}
      </p>
      {trip.note && <p>{trip.note}</p>}
      {trip.status === "alerted" && <Deliveries trip={trip} />}
      {trip.status === "safe" && trip.safe_at && (
        <p className="muted">Marked safe at {formatDateTime(trip.safe_at)}</p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="actions">
        {isOpen && (
          <button className="btn ok" onClick={() => run(markSafe(trip.id))}>
            I'm safe
          </button>
        )}
        {isActive && (
          <button
            className="btn secondary"
            onClick={() =>
              run(
                extendTrip({
                  id: trip.id,
                  deadline: new Date(deadline.getTime() + 15 * 60000).toISOString(),
                })
              )
            }
          >
            Extend 15 min
          </button>
        )}
        <button className="btn danger" onClick={onDelete}>
          Delete
        </button>
      </div>
    </div>
  );
}

export default function TripsPage() {
  const dispatch = useDispatch();
  const token = useSelector((s) => s.auth.token);
  const { items, status, error } = useSelector((s) => s.trips);
  const [acceptedBuddies, setAcceptedBuddies] = useState(null);

  useEffect(() => {
    dispatch(fetchTrips());
    const id = setInterval(() => dispatch(fetchTrips()), POLL_MS);
    return () => clearInterval(id);
  }, [dispatch]);

  useEffect(() => {
    api
      .listBuddies(token)
      .then((list) => setAcceptedBuddies(list.filter((b) => b.status === "confirmed").length))
      .catch(() => {});
  }, [token]);

  const open = items.filter((t) => t.status === "active" || t.status === "alerted");
  const past = items.filter((t) => t.status !== "active" && t.status !== "alerted");

  return (
    <Layout title="My trips" subtitle="Start a trip, and your buddies are alerted only if you don't check in.">
      {acceptedBuddies === 0 && (
        <p className="banner banner-warn" style={{ marginBottom: 14 }}>
          You have no accepted buddies yet, so nobody would be alerted. <Link to="/buddies">Add your buddies</Link>.
        </p>
      )}
      <TripForm />
      {error && <p className="error">{error}</p>}
      {status === "loading" && items.length === 0 && <p className="muted">Loading…</p>}
      {status !== "loading" && items.length === 0 && !error && (
        <div className="empty">No trips yet. Start your first one above.</div>
      )}
      {open.length > 0 && <div className="section-title">In progress</div>}
      {open.map((trip) => (
        <TripCard key={trip.id} trip={trip} />
      ))}
      {past.length > 0 && <div className="section-title">Past trips</div>}
      {past.map((trip) => (
        <TripCard key={trip.id} trip={trip} />
      ))}
    </Layout>
  );
}