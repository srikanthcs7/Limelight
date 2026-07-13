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

export function VisibilityTrend({ scores }: { scores: Score[] }) {
  const data = scores.map((s) => ({
    date: new Date(s.window_end).toLocaleDateString(),
    visibility: s.visibility_score,
  }));

  if (data.length === 0) {
    return <p className="muted">No scores yet — trigger a run with the CLI.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
        <XAxis dataKey="date" fontSize={12} />
        <YAxis domain={[0, 100]} fontSize={12} />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="visibility"
          stroke="#5b3df5"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
