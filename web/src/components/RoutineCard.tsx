import { useState } from "react";
import type { RoutineFull } from "../api";
import { MuscleBadge } from "./MuscleBadge";

function relativeDate(iso: string | null): string {
  if (!iso) return "Never performed";
  const d = new Date(`${iso}T00:00:00Z`);
  const today = new Date();
  const todayUtc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((todayUtc - d.getTime()) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

interface RoutineCardProps {
  routine: RoutineFull;
}

export function RoutineCard({ routine }: RoutineCardProps) {
  const [open, setOpen] = useState(false);
  const stale = routine.sessions_last_30d === 0;

  return (
    <div className={`card${stale ? " routine-card--stale" : ""}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none", border: "none", width: "100%", textAlign: "left",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          minHeight: 44,
        }}
      >
        <span>
          <div style={{ fontWeight: 600, fontSize: 16 }}>{routine.title}</div>
          <div className="routine-card__subtitle">
            Last performed {relativeDate(routine.last_performed)}
            {routine.sessions_last_30d > 0 && ` · ${routine.sessions_last_30d}× this month`}
          </div>
        </span>
        <span style={{ color: "var(--text-dim)" }}>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div style={{ marginTop: 8 }}>
          {routine.exercises.map((e) => (
            <div key={e.exercise} className="routine-card__exercise">
              <div className="routine-card__exercise-head">
                <MuscleBadge muscleGroup={e.muscle_group} />
                <span className="routine-card__exercise-name">{e.exercise}</span>
              </div>
              {e.notes && <div className="routine-card__notes">{e.notes}</div>}
              <table className="set-table">
                <thead>
                  <tr><th>Set</th><th>Reps</th><th>Rest</th></tr>
                </thead>
                <tbody>
                  {Array.from({ length: e.sets }, (_, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{e.reps}</td>
                      <td>{e.rest}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
