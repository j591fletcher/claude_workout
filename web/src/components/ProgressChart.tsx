import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ExerciseHistoryPoint } from "../api";

// Validated via dataviz skill's palette validator (lightness band + contrast)
// against the dark surface (--bg-elevated, #1c1c1e) — literal hex so it
// renders identically inside recharts' SVG attributes (unlike CSS vars,
// which SVG presentation attributes don't reliably resolve). Matches
// --chart-mark in index.css; kept separate from --accent because accent is
// tuned for text contrast, not the mark lightness band data needs.
const CHART_COLOR = "#3987e5";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function toEpoch(iso: string): number {
  return new Date(`${iso}T00:00:00Z`).getTime();
}

function monthLabelFromEpoch(epoch: number): string {
  const d = new Date(epoch);
  return `${MONTH_NAMES[d.getUTCMonth()]} '${String(d.getUTCFullYear()).slice(2)}`;
}

function fullDateFromEpoch(epoch: number): string {
  const d = new Date(epoch);
  return `${MONTH_NAMES[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

function monthKey(iso: string): string {
  return iso.slice(0, 7); // YYYY-MM
}

function monthLabelFromKey(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return `${MONTH_NAMES[m - 1]} '${String(y).slice(2)}`;
}

/** Sum volume per calendar month, filling in months with zero training
 * (never dropped) so a logging gap reads as a visible flat stretch instead
 * of two unrelated months sitting side by side. */
function monthlyVolume(points: ExerciseHistoryPoint[]): { label: string; value: number }[] {
  const withVolume = points.filter((p) => p.volume_lb !== null);
  if (withVolume.length === 0) return [];

  const sums = new Map<string, number>();
  for (const p of withVolume) {
    const key = monthKey(p.date);
    sums.set(key, (sums.get(key) ?? 0) + (p.volume_lb as number));
  }

  const [fy, fm] = monthKey(points[0].date).split("-").map(Number);
  const [ly, lm] = monthKey(points[points.length - 1].date).split("-").map(Number);
  const out: { label: string; value: number }[] = [];
  let y = fy, m = fm;
  while (y < ly || (y === ly && m <= lm)) {
    const key = `${y}-${String(m).padStart(2, "0")}`;
    out.push({ label: monthLabelFromKey(key), value: sums.get(key) ?? 0 });
    m += 1;
    if (m > 12) { m = 1; y += 1; }
  }
  return out;
}

interface ProgressChartProps {
  points: ExerciseHistoryPoint[];
}

export function ProgressChart({ points }: ProgressChartProps) {
  const weightSeries = points
    .filter((p) => p.top_weight_lb !== null)
    .map((p) => ({ x: toEpoch(p.date), value: p.top_weight_lb as number }));

  const volumeSeries = monthlyVolume(points);

  return (
    <div>
      <div className="section-title">Top set weight (lb)</div>
      {weightSeries.length === 0 ? (
        <div className="card">No weighted sessions logged for this exercise</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={weightSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={monthLabelFromEpoch}
              stroke="var(--text-dim)"
              fontSize={11}
              tickLine={false}
            />
            <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
              labelStyle={{ color: "var(--text)" }}
              labelFormatter={(value) => fullDateFromEpoch(Number(value))}
              formatter={(value) => [`${value} lb`, "Top weight"]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={CHART_COLOR}
              strokeWidth={2}
              dot={{ r: 4, fill: CHART_COLOR }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      <div className="section-title" style={{ marginTop: 20 }}>Monthly volume (lb)</div>
      {volumeSeries.length === 0 ? (
        <div className="card">No volume data for this exercise</div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={volumeSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap={2}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" stroke="var(--text-dim)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
              labelStyle={{ color: "var(--text)" }}
              formatter={(value) => [`${Number(value).toFixed(0)} lb`, "Volume"]}
            />
            <Bar dataKey="value" fill={CHART_COLOR} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
