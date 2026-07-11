import { useEffect, useState } from "react";
import { api, type DashboardStats, type WorkoutFeedItem, ApiError } from "../api";
import { StatTile } from "../components/StatTile";
import { LoadingSkeleton, ErrorNote } from "../components/StatusNote";

interface HomeProps {
  onGoToHistory: () => void;
}

export function Home({ onGoToHistory }: HomeProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<WorkoutFeedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.stats(), api.workouts(3, 0)])
      .then(([s, w]) => {
        setStats(s);
        setRecent(w);
      })
      .catch((e) => {
        setError(e instanceof ApiError ? "Hevy unreachable" : "Something went wrong loading your stats");
      });
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!stats || !recent) return <LoadingSkeleton lines={4} />;

  return (
    <div>
      <div className="section">
        <div className="stat-grid">
          <StatTile label="This week" value={stats.this_week} />
          <StatTile label="Streak" value={`${stats.streak_weeks} wk`} />
          <StatTile label="Total workouts" value={stats.total_workouts} />
          <StatTile
            label="Last workout"
            value={stats.last_workout ? stats.last_workout.title : "-"}
            sublabel={stats.last_workout?.date}
          />
        </div>
      </div>

      <div className="section">
        <div className="section-title">Recent PRs — max logged weight, not 1RM</div>
        <div className="pr-list">
          {stats.recent_prs.length === 0 && <div className="card">No PRs in the last 30 days</div>}
          {stats.recent_prs.map((e) => (
            <div key={e.exercise} className="card pr-item">
              <span className="pr-item__name">{e.exercise}</span>
              <span className="pr-item__weight">{e.weight} lb</span>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-title">Recent workouts</div>
        <div className="workout-list">
          {recent.map((w) => (
            <div key={`${w.date}-${w.title}`} className="card">
              <strong>{w.title}</strong> <span style={{ color: "var(--text-dim)" }}>{w.date}</span>
            </div>
          ))}
        </div>
        <button className="link-button" onClick={onGoToHistory}>See full history →</button>
      </div>
    </div>
  );
}
