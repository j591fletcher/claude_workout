import { useEffect, useState } from "react";
import { api, type ExerciseSummary, type ExerciseHistoryPoint, ApiError } from "../api";
import { ExercisePicker } from "../components/ExercisePicker";
import { ProgressChart } from "../components/ProgressChart";
import { LoadingSkeleton, ErrorNote } from "../components/StatusNote";
import { StatTile } from "../components/StatTile";

interface ProgressProps {
  preselected: string | null;
  onConsumePreselect: () => void;
}

export function Progress({ preselected, onConsumePreselect }: ProgressProps) {
  const [exercises, setExercises] = useState<ExerciseSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [history, setHistory] = useState<ExerciseHistoryPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.exercises()
      .then(setExercises)
      .catch(() => setError("Hevy unreachable"));
  }, []);

  useEffect(() => {
    if (preselected) {
      setSelected(preselected);
      onConsumePreselect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preselected]);

  useEffect(() => {
    if (!selected) return;
    setHistory(null);
    api.exerciseHistory(selected)
      .then(setHistory)
      .catch((e) => setError(e instanceof ApiError && e.status === 404
        ? `No logged history for ${selected}`
        : "Hevy unreachable"));
  }, [selected]);

  if (error) return <ErrorNote message={error} />;

  if (!selected) {
    if (!exercises) return <LoadingSkeleton lines={6} />;
    return <ExercisePicker exercises={exercises} onSelect={setSelected} />;
  }

  return (
    <div>
      <button className="link-button" onClick={() => setSelected(null)} style={{ marginBottom: 12 }}>
        ← Back to exercises
      </button>
      <h2>{selected}</h2>
      {!history ? (
        <LoadingSkeleton lines={4} />
      ) : (
        <>
          <ProgressSummary points={history} />
          <ProgressChart points={history} />
        </>
      )}
    </div>
  );
}

function ProgressSummary({ points }: { points: ExerciseHistoryPoint[] }) {
  const weighted = points.filter((p) => p.top_weight_lb !== null);
  const current = weighted.length ? weighted[weighted.length - 1].top_weight_lb : null;
  const first = weighted.length ? weighted[0].top_weight_lb : null;
  const delta = current !== null && first !== null ? current - first : null;

  return (
    <div className="progress-summary">
      <StatTile label="Current weight" value={current !== null ? `${current} lb` : "-"} />
      <StatTile label="Sessions" value={points.length} />
      <StatTile
        label="Since first logged"
        value={delta !== null ? `${delta > 0 ? "+" : ""}${delta} lb` : "-"}
      />
    </div>
  );
}
