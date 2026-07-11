// Hevy's API has no exercise images — this badge is the closest available
// stand-in, grouping the raw primary_muscle_group into a small set of
// contrast-checked, fixed-color categories (see index.css .muscle-badge--*).
const GROUP_MAP: Record<string, { label: string; variant: string }> = {
  chest: { label: "Chest", variant: "chest" },
  lats: { label: "Back", variant: "back" },
  upper_back: { label: "Back", variant: "back" },
  lower_back: { label: "Back", variant: "back" },
  traps: { label: "Back", variant: "back" },
  shoulders: { label: "Shoulders", variant: "shoulders" },
  biceps: { label: "Arms", variant: "arms" },
  triceps: { label: "Arms", variant: "arms" },
  forearms: { label: "Arms", variant: "arms" },
  quadriceps: { label: "Legs", variant: "legs" },
  hamstrings: { label: "Legs", variant: "legs" },
  glutes: { label: "Legs", variant: "legs" },
  calves: { label: "Legs", variant: "legs" },
  abductors: { label: "Legs", variant: "legs" },
  adductors: { label: "Legs", variant: "legs" },
  abdominals: { label: "Core", variant: "core" },
};

export function MuscleBadge({ muscleGroup }: { muscleGroup: string | null }) {
  const entry = muscleGroup ? GROUP_MAP[muscleGroup] : undefined;
  const label = entry?.label ?? "Other";
  const variant = entry?.variant ?? "other";
  return (
    <span className={`muscle-badge muscle-badge--${variant}`} title={label}>
      {label[0]}
    </span>
  );
}
