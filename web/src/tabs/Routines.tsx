import { useEffect, useState } from "react";
import { api, type RoutineFull } from "../api";
import { RoutineCard } from "../components/RoutineCard";
import { LoadingSkeleton, ErrorNote } from "../components/StatusNote";

export function Routines() {
  const [routines, setRoutines] = useState<RoutineFull[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.routinesFull().then(setRoutines).catch(() => setError("Hevy unreachable"));
  }, []);

  if (error) return <ErrorNote message={error} />;
  if (!routines) return <LoadingSkeleton lines={5} />;

  return (
    <div className="workout-list">
      {routines.map((r) => (
        <RoutineCard key={r.title} routine={r} />
      ))}
    </div>
  );
}
