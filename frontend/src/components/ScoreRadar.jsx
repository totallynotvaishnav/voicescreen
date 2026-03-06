import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

export default function ScoreRadar({ score }) {
  if (!score) return null;

  const data = [
    { dimension: 'Communication', value: score.communication, fullMark: 10 },
    { dimension: 'Experience', value: score.experience, fullMark: 10 },
    { dimension: 'Motivation', value: score.motivation, fullMark: 10 },
    { dimension: 'Availability', value: score.availability, fullMark: 10 },
    { dimension: 'Cultural Fit', value: score.cultural_fit, fullMark: 10 },
    { dimension: 'Role Fit', value: score.role_fit, fullMark: 10 },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 500 }}
        />
        <PolarRadiusAxis
          domain={[0, 10]}
          tick={{ fill: '#64748b', fontSize: 10 }}
          axisLine={false}
        />
        <Radar
          name="Score"
          dataKey="value"
          stroke="#6366f1"
          fill="rgba(99, 102, 241, 0.25)"
          strokeWidth={2}
          dot={{ fill: '#818cf8', r: 4 }}
        />
        <Tooltip
          contentStyle={{
            background: '#1e293b',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            color: '#f1f5f9',
            fontSize: 13,
          }}
          formatter={(value) => [value.toFixed(1), 'Score']}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
