import React, { useEffect } from 'react';
import { useSocket } from '../../hooks/useSocket';
import { useFinancialStore } from '../../store/financialStore';
import { Row, Col } from 'antd';
import { RiseOutlined } from '@ant-design/icons';

export const NPVDashboard: React.FC = () => {
  const { emit, on } = useSocket();
  const budget = useFinancialStore(state => state.budget);
  const npvResults = useFinancialStore(state => state.npvResults);
  const setNpvResults = useFinancialStore(state => state.setNpvResults);

  useEffect(() => {
    const off = on("financial_result", (data) => {
      setNpvResults(data);
    });
    emit("financial_update", budget);
    return () => { off(); };
  }, [on, emit, setNpvResults, budget]);

  if (!npvResults) return null;

  const ai = npvResults.ai;

  return (
    <div className="w-full flex-grow bg-gradient-to-br from-slate-900 via-[#0f172a] to-blue-900 rounded-3xl p-5 md:p-6 shadow-[0_15px_40px_rgba(30,58,138,0.3)] border border-blue-500/20 relative overflow-hidden transform transition-transform hover:scale-[1.01] duration-500">
      {/* Decorative optimistic flares */}
      <div className="absolute top-[-50%] right-[-20%] w-96 h-96 bg-emerald-500/20 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-[-30%] left-[-10%] w-64 h-64 bg-blue-500/20 rounded-full blur-[80px] pointer-events-none"></div>
      
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 mb-5">
        <h2 className="text-lg md:text-xl font-bold tracking-wide text-white flex items-center gap-3">
          <RiseOutlined className="text-emerald-400 text-3xl" /> 
          AI Valuation Model
        </h2>
        <span className="bg-emerald-500/20 border border-emerald-500/50 px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest text-emerald-300 uppercase shadow-[0_0_15px_rgba(16,185,129,0.4)] whitespace-nowrap">
          Prime Asset 🚀
        </span>
      </div>

      <Row gutter={[14, 14]} className="relative z-10 w-full">
        <Col xs={24} xl={12}>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 md:p-5 h-full">
            <p className="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em] mb-3 opacity-80">Projected NPV</p>
            <div className="leading-none break-words">
              <span className="font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-300 to-teal-500 drop-shadow-sm text-[clamp(2.2rem,7vw,4.2rem)]">
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(ai.npv))}
              </span>
              <span className="ml-2 align-baseline font-extrabold text-emerald-400/90 text-[clamp(1.1rem,2.8vw,1.9rem)]">M</span>
            </div>
          </div>
        </Col>
        <Col xs={24} xl={12}>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 md:p-5 h-full">
            <p className="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em] mb-3 opacity-80">Expected IRR</p>
            <div className="leading-none whitespace-nowrap">
              <span className="font-extrabold text-white text-[clamp(2.2rem,7vw,4.2rem)]">{Number(ai.irr).toFixed(1)}%</span>
              <span className="ml-2 text-lg text-emerald-400 animate-bounce inline-block">▲</span>
            </div>
          </div>
        </Col>
        <Col xs={24} xl={12}>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 md:p-5 h-full">
            <p className="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em] mb-3 opacity-80">Payback Period</p>
            <div className="leading-none">
              <span className="font-extrabold text-white drop-shadow-sm text-[clamp(1.9rem,5.6vw,3.2rem)]">{Number(ai.payback_year).toFixed(1)}</span>
              <span className="ml-2 font-semibold text-blue-300 text-[clamp(1rem,2.6vw,1.35rem)]">Years</span>
            </div>
          </div>
        </Col>
        <Col xs={24} xl={12}>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 md:p-5 h-full">
            <p className="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em] mb-3 opacity-80">Capital Efficiency</p>
            <div className="leading-none">
              <span className="font-extrabold text-white drop-shadow-sm text-[clamp(1.9rem,5.6vw,3.2rem)]">{Number(ai.capital_efficiency).toFixed(2)}x</span>
              <span className="ml-2 font-semibold text-emerald-400 text-[clamp(1rem,2.6vw,1.35rem)]">ROI</span>
            </div>
          </div>
        </Col>
      </Row>
    </div>
  );
};
