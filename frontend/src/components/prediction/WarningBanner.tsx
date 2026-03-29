import React from 'react';
import { Typography } from 'antd';
import { usePredictionStore } from '../../store/predictionStore';

const { Text } = Typography;

export const WarningBanner: React.FC = () => {
  const result = usePredictionStore(state => state.result);

  if (!result) return null;

  return (
    <div className="w-full mt-2">
      {result.warnings && result.warnings.length > 0 ? (
        <div className="w-full bg-red-50/50 backdrop-blur-sm mt-4 p-5 rounded-2xl text-left animate-slide-up border border-red-100 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">⚠️</span>
            <Text type="danger" strong className="text-[15px]">Risk Analysis Report</Text>
          </div>
          <ul className="space-y-2 ml-1">
            {result.warnings.map((w, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-sm text-red-800 bg-white/60 p-2 rounded-lg border border-red-100/50">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0 shadow-sm"></span>
                <span className="font-medium leading-tight">{w}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="w-full bg-emerald-50/50 backdrop-blur-sm border border-emerald-100 p-5 rounded-2xl text-center mt-4 animate-slide-up shadow-sm">
          <Text type="success" strong className="flex items-center justify-center gap-2 text-[15px]">
            <span className="text-xl">✨</span> Optimal candidate profile
          </Text>
          <Text className="block text-xs mt-1 text-emerald-600/80">All biochemical parameters are within safe ranges.</Text>
        </div>
      )}
    </div>
  );
};
