import { useEffect, useState } from "react";
import { api, type DashboardStats, type WorkoutFeedItem, ApiError } from "../api";
import { StatTile } from "../components/StatTile";
import { LoadingSkeleton, ErrorNote } from "../components/StatusNote";
import { WorkoutCalendar } from "../components/WorkoutCalendar";
import { BottomSheet } from "../components/BottomSheet";
import { WorkoutCard } from "../components/WorkoutCard";

interface HomeProps {
  onSelectExercise: (name: string) => void;
}

export function Home({ onSelectExercise }: HomeProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prsExpanded, setPrsExpanded] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dayWorkouts, setDayWorkouts] = useState<WorkoutFeedItem[] | null>(null);
  const [dayError, setDayError] = useState<string | null>(null);

  useEffect(() => {
    api.stats()
      .then(setStats)
      .catch((e) => setError(e instanceof ApiError ? "Hevy unreachable" : "Something went wrong loading your stats"));
  }, []);

  function openDay(date: string) {
    setSelectedDate(date);
    setDayWorkouts(null);
    setDayError(null);
    api.workoutsByDate(date)
      .then(setDayWorkouts)
      .catch(() => setDayError("Couldn't load that day's workout"));
  }

  if (error) return <ErrorNote message={error} />;

  return (
    <div>
      <div className="section">
        <WorkoutCalendar onSelectDay={openDay} />
      </div>

      {!stats ? (
        <LoadingSkeleton lines={4} />
      ) : (
        <>
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
            <button className="card pr-disclosure" onClick={() => setPrsExpanded((p) => !p)}>
              <span>🏆 {stats.recent_prs.length} PRs in the last 30 days</span>
              <span className="pr-disclosure__chevron">{prsExpanded ? "−" : "+"}</span>
            </button>
            {prsExpanded && (
              <div className="pr-list" style={{ marginTop: 8 }}>
                <div className="section-title">Max logged weight — not 1RM</div>
                {stats.recent_prs.length === 0 && <div className="card">No PRs in the last 30 days</div>}
                {stats.recent_prs.map((e) => (
                  <div key={e.exercise} className="card pr-item">
                    <span className="pr-item__name">{e.exercise}</span>
                    <span className="pr-item__weight">{e.weight} lb</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <BottomSheet open={selectedDate !== null} onClose={() => setSelectedDate(null)}>
        {dayError && <ErrorNote message={dayError} />}
        {!dayError && !dayWorkouts && <LoadingSkeleton lines={3} />}
        {dayWorkouts && (
          <div className="workout-list">
            {dayWorkouts.map((w) => (
              <WorkoutCard key={`${w.date}-${w.title}`} workout={w} onSelectExercise={onSelectExercise} />
            ))}
          </div>
        )}
      </BottomSheet>
    </div>
  );
}
