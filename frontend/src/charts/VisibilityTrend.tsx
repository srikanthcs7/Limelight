import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Score } from "../api/client";

const ACCENT = "#5e5ce6";

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div className="v">{payload[0].value} / 100</div>
    </div>
  );
}

export function VisibilityTrend({ scores }: { scores: Score[] }) {
  const data = scores.map((s) => ({
    date: new Date(s.window_end).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    visibility: s.visibility_score,
  }));

  if (data.length === 0) {
    return <p className="muted">No scores yet — run the tracker to plot a trend.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--ink-3)", fontSize: 12 }}
          dy={6}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 25, 50, 75, 100]}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--ink-3)", fontSize: 12 }}
          width={40}
        />
        <Tooltip content={<Tip />} cursor={{ stroke: "var(--ink-3)", strokeDasharray: "3 3" }} />
        <Line
          type="monotone"
          dataKey="visibility"
          stroke={ACCENT}
          strokeWidth={2}
          dot={{ r: 4, fill: ACCENT, stroke: "var(--surface)", strokeWidth: 2 }}
          activeDot={{ r: 6, fill: ACCENT, stroke: "var(--surface)", strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
