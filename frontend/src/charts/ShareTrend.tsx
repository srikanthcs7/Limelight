import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SovTimeline } from "../api/client";

// dataviz validated categorical order (light mode), CVD-safe.
const PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948"];

export function ShareTrend({ timeline }: { timeline: SovTimeline }) {
  const { days, series } = timeline;
  if (days.length === 0 || series.length === 0) {
    return <p className="muted">No share-of-voice history yet — runs accumulate a trend over days.</p>;
  }

  const data = days.map((d, i) => {
    const row: Record<string, number | string> = {
      date: new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    };
    for (const s of series) row[s.name] = Math.round(s.points[i] * 100);
    return row;
  });

  // brand first so it takes slot 1 and a bolder stroke.
  const ordered = [...series].sort((a, b) => Number(b.is_tracked_brand) - Number(a.is_tracked_brand));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: "var(--ink-3)", fontSize: 12 }} dy={6} />
        <YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: "var(--ink-3)", fontSize: 12 }} width={40} unit="%" />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 13,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {ordered.map((s, i) => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={s.is_tracked_brand ? 3 : 1.75}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
