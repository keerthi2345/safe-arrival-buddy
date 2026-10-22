const LABELS = { active: "Active", safe: "Safe", alerted: "Alerted", resolved: "Resolved" };

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] || status}</span>;
}