import { useState } from "react";
import type { RoutineFull } from "../api";

interface RoutineCardProps {
  routine: RoutineFull;
}

export function RoutineCard({ routine }: RoutineCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card">
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: "none", border: "none", width: "100%", textAlign: "left",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          minHeight: 44, fontWeight: 600, fontSize: 16,
        }}
      >
        {routine.title}
        <span style={{ color: "var(--text-dim)" }}>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div>
          {routine.exercises.map((e) => (
            <div key={e.exercise} className="exercise-row" style={{ flexDirection: "column", alignItems: "stretch", gap: 2 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>{e.exercise}</span>
                <span>{e.sets}x{e.reps} | rest {e.rest}</span>
              </div>
              {e.notes && <div style={{ color: "var(--text-dim)", fontSize: 12 }}>{e.notes}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
