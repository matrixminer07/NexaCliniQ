import React from 'react';
import { Progress, Typography } from 'antd';
import { usePredictionStore } from '../../store/predictionStore';

const { Title, Text } = Typography;

export const ProbabilityGauge: React.FC = () => {
  const result = usePredictionStore(state => state.result);

  if (!result) return null;

  const percent = Math.round(result.success_probability * 100);
  const isHigh = percent > 60;

  return (
    <div className="flex justify-center flex-col items-center py-8">
      <div className="relative transform transition-transform duration-700 hover:scale-105 group cursor-default">
        {/* Huge energetic background bloom */}
        <div className={`absolute inset-0 ${isHigh ? 'bg-emerald-400/30' : 'bg-orange-400/20'} rounded-full blur-[60px] scale-150 group-hover:scale-[1.8] group-hover:opacity-100 opacity-80 transition-all duration-700`}></div>
        <Progress 
          type="dashboard" 
          percent={percent} 
          gapDegree={120} 
          size={280}
          strokeWidth={14}
          strokeColor={{
            '0%': isHigh ? '#34d399' : '#fba918',
            '100%': isHigh ? '#059669' : '#ea580c',
          }}
          trailColor="#f1f5f9"
          format={(val) => (
             <div className="flex flex-col items-center justify-center">
               <span className={`text-6xl font-black tracking-tighter bg-clip-text text-transparent ${isHigh ? 'bg-gradient-to-br from-emerald-400 to-teal-700' : 'bg-gradient-to-br from-orange-400 to-red-600'}`}>
                 {val}%
               </span>
             </div>
          )}
        />
        <div className="absolute inset-0 flex items-center justify-center flex-col pointer-events-none mt-[100px]">
          <Text className="text-slate-400 font-bold tracking-widest uppercase text-[10px] mt-10 text-center leading-tight">
            Probability of Success
          </Text>
        </div>
        <div className="mt-8 text-center">
           <span className={`px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.2em] shadow-lg ${isHigh ? 'bg-gradient-to-r from-emerald-100 to-teal-50 text-emerald-800 border border-emerald-200' : 'bg-gradient-to-r from-orange-100 to-red-50 text-orange-800 border border-orange-200'}`}>
             {isHigh ? 'Highly Viable Candidate 🚀' : 'High Risk Profile ⚠️'}
           </span>
        </div>
      </div>
    </div>
  );
};
