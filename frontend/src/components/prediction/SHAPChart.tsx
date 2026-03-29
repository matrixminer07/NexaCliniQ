import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { usePredictionStore } from '../../store/predictionStore';
import { Typography } from 'antd';

const { Title } = Typography;

export const SHAPChart: React.FC = () => {
  const result = usePredictionStore(state => state.result);

  if (!result) return null;

  const shapValues = result.shap_values
    ? Object.entries(result.shap_values).map(([key, value]) => ({
        name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        impact: Number(value),
      }))
    : [];

  const breakdownValues = (result.shap_breakdown?.contributions ?? []).map((c) => ({
    name: c.feature.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    impact: Number(c.shap),
  }));

  // Prefer explicit shap_values; fallback to shap_breakdown contributions.
  const data = (shapValues.length > 0 ? shapValues : breakdownValues)
    .filter((d) => Number.isFinite(d.impact))
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  if (data.length === 0) {
    return <div className="text-center text-gray-400 py-6">No data available</div>;
  }

  return (
    <div className="w-full flex-grow bg-white/60 rounded-2xl p-6 border border-gray-100 shadow-sm flex flex-col">
      <Title level={5} className="!text-sm !font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Feature Impact Analysis (SHAP)
      </Title>
      <div style={{ height: 300, width: '100%' }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart layout="vertical" data={data} margin={{ top: 5, right: 20, left: 18, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
          <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 12 }} />
          <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(val: any) => Number(val).toFixed(3)} cursor={{ fill: '#f3f4f6' }} />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.impact > 0 ? '#52c41a' : '#ff4d4f'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
};
