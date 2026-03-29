import React, { useEffect } from 'react';
import { useSocket } from '../../hooks/useSocket';
import { useFinancialStore } from '../../store/financialStore';
import { Card, Typography, Spin } from 'antd';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { LineChartOutlined } from '@ant-design/icons';

const { Text } = Typography;

export const MonteCarloHistogram: React.FC = () => {
  const { emit, on } = useSocket();
  const budget = useFinancialStore(s => s.budget);
  const dataList = useFinancialStore(s => s.monteCarloData);
  const addData = useFinancialStore(s => s.setMonteCarloData);
  const clearData = useFinancialStore(s => s.clearMonteCarloData);

  useEffect(() => {
    // When budget changes, restart Monte Carlo
    clearData();
    const off = on("montecarlo_batch", (res: any) => {
      addData([res]);
    });
    emit("run_montecarlo", budget);

    return () => { off(); };
  }, [budget, emit, on, clearData, addData]);

  // The latest batch has the accumulated histogram
  const latestBatch = dataList.length > 0 ? dataList[dataList.length - 1] : null;

  if (!latestBatch) {
    return (
      <Card className="shadow-[0_2px_10px_rgba(0,0,0,0.02)] border border-gray-200/50 rounded-2xl h-80 flex items-center justify-center">
        <Spin tip="Running 5000+ Monte Carlo Scenarios..." />
      </Card>
    );
  }

  // Format Recharts data
  const { histogram, bin_edges, p10, p50, p90, scenarios_complete } = latestBatch;
  const chartData = histogram.map((count: number, idx: number) => ({
    npv: Math.round((bin_edges[idx] + bin_edges[idx+1]) / 2),
    count: count
  }));

  return (
    <Card 
      className="shadow-[0_2px_10px_rgba(0,0,0,0.02)] border border-gray-200/50 rounded-2xl w-full"
      title={<span className="font-semibold text-gray-700 flex items-center gap-2 tracking-wide text-sm"><LineChartOutlined className="text-blue-500" /> Monte Carlo Simulation</span>}
      extra={<Text className="text-[10px] font-mono text-gray-500 bg-gray-100 px-3 py-1 rounded-full">{scenarios_complete} / 5000 run</Text>}
    >
      <div className="flex justify-between items-center px-1 mb-4">
        <div className="text-center"><Text className="text-[10px] text-gray-400 block uppercase tracking-wider mb-0.5">P10 (Downside)</Text><span className="font-mono text-red-500 font-semibold text-sm">₹{p10}M</span></div>
        <div className="text-center"><Text className="text-[10px] text-blue-400 block uppercase tracking-wider mb-0.5">P50 (Expected)</Text><span className="font-mono text-blue-600 font-bold text-lg">₹{p50}M</span></div>
        <div className="text-center"><Text className="text-[10px] text-gray-400 block uppercase tracking-wider mb-0.5">P90 (Upside)</Text><span className="font-mono text-emerald-500 font-semibold text-sm">₹{p90}M</span></div>
      </div>
      <div style={{ width: '100%', height: 300, marginTop: 12 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1677ff" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#1677ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis dataKey="npv" tickFormatter={(val) => `₹${val}M`} tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <Tooltip formatter={(val: any) => [val, 'Scenarios']} labelFormatter={(l) => `NPV: ₹${l}M`} />
            <Area type="monotone" dataKey="count" stroke="#1677ff" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
