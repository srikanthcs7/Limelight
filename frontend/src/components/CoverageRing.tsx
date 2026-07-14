/** SVG donut: share of prompts where the brand appears. */
export function CoverageRing({ mentioned, total }: { mentioned: number; total: number }) {
  const pct = total > 0 ? mentioned / total : 0;
  const size = 96;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * pct;

  return (
    <div className="ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="22"
          fontWeight="700"
          fill="var(--ink)"
        >
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <div className="ring-label">
        <b>
          {mentioned}/{total}
        </b>{" "}
        prompts mention you
      </div>
    </div>
  );
}
