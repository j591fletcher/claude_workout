import { useMemo, useState } from "react";
import type { ExerciseSummary } from "../api";

interface ExercisePickerProps {
  exercises: ExerciseSummary[];
  onSelect: (name: string) => void;
}

export function ExercisePicker({ exercises, onSelect }: ExercisePickerProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return exercises;
    return exercises.filter((e) => e.name.toLowerCase().includes(q));
  }, [exercises, query]);

  return (
    <div>
      <input
        type="search"
        placeholder="Search exercises…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="search-input"
      />
      <div className="exercise-picker-list">
        {filtered.map((e) => (
          <button key={e.name} className="exercise-picker-item" onClick={() => onSelect(e.name)}>
            <span>{e.name}</span>
            <span style={{ color: "var(--text-dim)", fontSize: 12 }}>{e.sessions} sessions</span>
          </button>
        ))}
      </div>
    </div>
  );
}
