import React from 'react';
import { usePredictionStore } from '../../store/predictionStore';
import { Typography, Row, Col, Progress } from 'antd';

const { Title, Text } = Typography;

export const AttritionWaterfall: React.FC = () => {
  const result = usePredictionStore(state => state.result);

  if (!result || !result.phase_probabilities) return null;
  const p = result.phase_probabilities;

  return (
    <div className="w-full flex-grow bg-white/60 p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
      <Title level={5} className="!text-sm !font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Phase Success Probabilities
      </Title>
      
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <div className="flex flex-col items-center p-3 bg-blue-50/50 rounded-xl border border-blue-100">
            <Text className="text-[10px] text-blue-600 font-bold tracking-wide uppercase mb-2">Phase I</Text>
            <Progress type="circle" percent={p.phase1} size={50} strokeColor="#3b82f6" format={(percent) => <span className="text-xs font-semibold text-slate-700">{percent}%</span>} />
          </div>
        </Col>
        <Col span={8}>
          <div className="flex flex-col items-center p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
            <Text className="text-[10px] text-indigo-600 font-bold tracking-wide uppercase mb-2">Phase II</Text>
            <Progress type="circle" percent={p.phase2} size={50} strokeColor="#6366f1" format={(percent) => <span className="text-xs font-semibold text-slate-700">{percent}%</span>} />
          </div>
        </Col>
        <Col span={8}>
          <div className="flex flex-col items-center p-3 bg-violet-50/50 rounded-xl border border-violet-100">
            <Text className="text-[10px] text-violet-600 font-bold tracking-wide uppercase mb-2">Phase III</Text>
            <Progress type="circle" percent={p.phase3} size={50} strokeColor="#8b5cf6" format={(percent) => <span className="text-xs font-semibold text-slate-700">{percent}%</span>} />
          </div>
        </Col>
      </Row>

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <Text className="text-sm text-gray-500 font-medium">Uplift vs Baseline</Text>
        <div className="bg-emerald-100 text-emerald-700 font-bold px-3 py-1 rounded-full text-xs">
          {p.uplift_vs_baseline}x Multiplier
        </div>
      </div>
    </div>
  );
};
