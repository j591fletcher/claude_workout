import type { WorkoutFeedItem } from "../api";
import { MuscleBadge } from "./MuscleBadge";

function weightLabel(weight: number | null): string {
  return weight === null ? "bodyweight" : `${weight} lb`;
}

interface WorkoutCardProps {
  workout: WorkoutFeedItem;
  onSelectExercise: (name: string) => void;
}

export function WorkoutCard({ workout, onSelectExercise }: WorkoutCardProps) {
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <strong>{workout.title}</strong>
        <span style={{ color: "var(--text-dim)", fontSize: 13 }}>
          {workout.date}{!workout.tracked && " · untracked"}
        </span>
      </div>
      {workout.exercises.map((e) => (
        <div key={e.exercise} className="exercise-row">
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <MuscleBadge muscleGroup={e.muscle_group} />
            <button className="link-button" onClick={() => onSelectExercise(e.exercise)}>
              {e.exercise}
            </button>
          </span>
          <span>
            {e.sets}x{e.reps} | {weightLabel(e.weight)} | RPE {e.rpe}
          </span>
        </div>
      ))}
    </div>
  );
}
