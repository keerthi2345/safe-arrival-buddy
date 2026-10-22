import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import PublicShell from "../components/PublicShell.jsx";
import { api } from "../api";

export default function ConfirmPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function onAccept() {
    setState("loading");
    try {
      setResult(await api.confirmBuddy(token));
      setState("done");
    } catch (e) {
      setError(e.message);
      setState("error");
    }
  }

  return (
    <PublicShell>
      <div className="card">
        {!token && <p className="error">This link is missing its token. Please open the link from your email again.</p>}

        {token && (state === "idle" || state === "loading") && (
          <>
            <h2>You've been asked to be a safe-arrival buddy</h2>
            <p className="muted">
              If you accept, you'll get an email only if this traveller doesn't check in on time. You don't need an
              account, and you can't see their location.
            </p>
            <button className="btn ok block" onClick={onAccept} disabled={state === "loading"}>
              {state === "loading" ? "Confirming…" : "Accept"}
            </button>
          </>
        )}

        {state === "done" && (
          <div className="hero hero-ok" style={{ marginBottom: 0 }}>
            <div className="hero-icon">✓</div>
            <div>
              <h2>You're all set, {result.buddy_name}</h2>
              <p>You're now a buddy for {result.traveller_name}. You'll be emailed if they don't arrive on time.</p>
            </div>
          </div>
        )}

        {state === "error" && <p className="banner banner-alert">{error}</p>}
      </div>
    </PublicShell>
  );
}