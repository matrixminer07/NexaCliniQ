import React, { useEffect, useRef } from 'react';
import { useSocket } from '../../hooks/useSocket';
import { useFinancialStore } from '../../store/financialStore';
import { Card } from 'antd';
import * as d3 from 'd3';
import { formatMillions } from '@/utils/numberFormat';

interface TornadoBar {
  label: string;
  swing: number;
}

export const TornadoChart: React.FC = () => {
  const { emit, on } = useSocket();
  const budget = useFinancialStore(s => s.budget);
  const data = useFinancialStore(s => s.sensitivityData);
  const setData = useFinancialStore(s => s.setSensitivityData);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const off = on("sensitivity_result", (res) => {
      setData(res);
    });
    emit("run_sensitivity", budget);
    return () => { off(); };
  }, [on, emit, setData, budget]);

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const bars = data.bars as TornadoBar[];
    
    // Clear previous D3 render
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 450, height = 300;
    const margin = { top: 20, right: 30, bottom: 20, left: 120 };

    const y = d3.scaleBand()
      .domain(bars.map((d) => d.label))
      .range([margin.top, height - margin.bottom])
      .padding(0.2);

    const maxAbsSwing = d3.max(bars, (d) => Math.abs(d.swing)) as number;
    const x = d3.scaleLinear()
      .domain([-maxAbsSwing * 1.1, maxAbsSwing * 1.1])
      .range([margin.left, width - margin.right]);

    const moneyTickFormat = (value: d3.NumberValue): string => formatMillions(Number(value), 0);

    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(moneyTickFormat))
      .attr("color", "#9ca3af");

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll("text")
      .style("font-size", "11px")
      .attr("fill", "#6b7280");

    // Center Baseline
    svg.append("line")
      .attr("x1", x(0))
      .attr("x2", x(0))
      .attr("y1", margin.top)
      .attr("y2", height - margin.bottom)
      .attr("stroke", "#d1d5db")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "4,4");

    // Dynamic Bars
    svg.selectAll(".bar")
      .data(bars)
      .join("rect")
      .attr("class", "bar")
      .attr("y", (d: TornadoBar) => y(d.label) as number)
      .attr("height", y.bandwidth())
      .attr("x", (d: TornadoBar) => (d.swing < 0 ? x(d.swing) : x(0)))
      .attr("width", (d: TornadoBar) => Math.abs(x(d.swing) - x(0)))
      .attr("fill", (d: TornadoBar) => (d.swing < 0 ? "#ff4d4f" : "#1677ff"))
      .attr("rx", 3); // rounded corners

  }, [data]);

  return (
    <Card 
      className="shadow-[0_2px_10px_rgba(0,0,0,0.02)] border border-gray-200/50 rounded-2xl w-full" 
      title={<span className="font-semibold text-gray-700 tracking-wide text-sm">Sensitivity Analysis (Tornado)</span>}
    >
      <div className="flex justify-center w-full overflow-hidden">
        <svg ref={svgRef} width="450" height="300"></svg>
      </div>
    </Card>
  );
};
