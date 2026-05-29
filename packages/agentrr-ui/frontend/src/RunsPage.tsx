import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { friendlySessionName, home } from "./copy";
import PageHeader from "./components/PageHeader";
import { fetchRuns, type RunSummary } from "./api";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchRuns()
      .then(setRuns)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <PageHeader title={home.title} helpTip={home.aboutTip}>
        <button type="button" className="btn" onClick={load} disabled={loading}>
          {loading ? "Loading…" : home.refresh}
        </button>
      </PageHeader>

      {error && (
        <div className="alert alert-error" role="alert">
          <strong>{home.loadErrorTitle}</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && runs.length === 0 && !error && (
        <div className="empty">
          <p className="empty-title">{home.emptyTitle}</p>
          <p className="empty-text">{home.emptyBody}</p>
        </div>
      )}

      <ul className="session-list">
        {runs.map((r) => (
          <li key={r.run_id}>
            <Link to={`/runs/${encodeURIComponent(r.run_id)}`} className="session-card">
              <div className="session-card-main">
                <h2 className="session-card-title">{friendlySessionName(r.run_id)}</h2>
                <p className="session-card-meta">
                  {r.event_count} steps · {formatTime(r.mtime_iso)}
                  {r.truncated ? ` · ${home.incomplete}` : ""}
                </p>
              </div>
              <span className="session-card-arrow" aria-hidden>
                →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
