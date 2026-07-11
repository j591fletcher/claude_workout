import type { Source } from "../api";

const LABELS: Record<Source, string> = {
  nippard: "from your Nippard program",
  hevy: "from your logged data",
  coaching: "general coaching",
};

export function SourceBadge({ source }: { source: Source }) {
  return <span className={`source-badge source-badge--${source}`}>{LABELS[source]}</span>;
}
