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
// against both the dark (#1c1c1e) and light (#ffffff) surfaces — literal hex
// so it renders identically inside recharts' SVG attributes (unlike CSS vars,
// which SVG presentation attributes don't reliably resolve).
const CHART_COLOR = "#e8672a";

interface ProgressChartProps {
  points: ExerciseHistoryPoint[];
}

function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${m}/${d}`;
}

export function ProgressChart({ points }: ProgressChartProps) {
  const weightSeries = points
    .filter((p) => p.top_weight_lb !== null)
    .map((p) => ({ date: shortDate(p.date), value: p.top_weight_lb as number }));

  const volumeSeries = points
    .filter((p) => p.volume_lb !== null)
    .map((p) => ({ date: shortDate(p.date), value: p.volume_lb as number }));

  return (
    <div>
      <div className="section-title">Top set weight (lb)</div>
      {weightSeries.length === 0 ? (
        <div className="card">No weighted sessions logged for this exercise</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={weightSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8 }}
              labelStyle={{ color: "var(--text)" }}
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

      <div className="section-title" style={{ marginTop: 20 }}>Session volume (lb)</div>
      {volumeSeries.length === 0 ? (
        <div className="card">No volume data for this exercise</div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={volumeSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap={2}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={11} tickLine={false} />
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
