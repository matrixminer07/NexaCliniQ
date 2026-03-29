import React, { useEffect } from 'react';
import { Slider, Typography, Card, Badge, Tooltip } from 'antd';
import { InfoCircleOutlined, ExperimentOutlined } from '@ant-design/icons';
import { usePredictionStore } from '../../store/predictionStore';

const { Text } = Typography;

const getRiskLevel = (name: string, value: number) => {
  if (name === 'toxicity') return value > 0.6 ? 'High' : value > 0.3 ? 'Medium' : 'Low';
  if (name === 'bioavailability') return value < 0.4 ? 'High' : value < 0.7 ? 'Medium' : 'Low';
  return 'Optimal';
};

const getRiskColor = (name: string, value: number): "success" | "warning" | "error" | "default" => {
  const risk = getRiskLevel(name, value);
  if (risk === 'High') return 'error';
  if (risk === 'Medium') return 'warning';
  if (risk === 'Optimal') return 'success';
  return 'default';
};

export const PredictionSliders: React.FC = () => {
  const inputs = usePredictionStore(state => state.inputs);
  const setInputs = usePredictionStore(state => state.setInputs);
  // Legacy panel: this store updates local slider state only.
  useEffect(() => {}, []);

  const handleSliderChange = (name: keyof typeof inputs, value: number) => {
    const newInputs = { ...inputs, [name]: value };
    setInputs(newInputs);
  };

  const names: Record<keyof typeof inputs, string> = {
    toxicity: "Toxicity Level",
    bioavailability: "Bioavailability",
    solubility: "Solubility",
    binding: "Binding Affinity",
    molecular_weight: "Molecular Weight"
  };

  const colors: Record<keyof typeof inputs, string> = {
    toxicity: "#f5222d",
    bioavailability: "#52c41a",
    solubility: "#1677ff",
    binding: "#fa541c",
    molecular_weight: "#722ed1"
  };

  return (
    <Card 
      className="shadow-[0_2px_10px_rgba(0,0,0,0.02)] border border-gray-200/50 rounded-2xl overflow-hidden hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] transition-shadow duration-300"
      styles={{ header: { backgroundColor: '#ffffff', borderBottom: '1px solid #f8f9fa' }, body: { padding: '24px 32px' } }}
      title={<span className="font-semibold text-gray-700 flex items-center gap-2"><ExperimentOutlined className="text-indigo-500" /> Molecular Properties Configuration</span>}
    >
      <div className="space-y-4">
        {(Object.entries(inputs) as [keyof typeof inputs, number][]).map(([key, value]) => {
          const isRiskFeature = ['toxicity', 'bioavailability'].includes(key);
          return (
            <div key={key} className="group py-2 px-3 -mx-3 rounded-xl hover:bg-slate-50/80 transition-all duration-300 border border-transparent hover:border-slate-100">
              <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-2">
                  <Text className="font-medium text-gray-700">{names[key]}</Text>
                  <Tooltip title={`Adjust the ${names[key].toLowerCase()} of the candidate compound.`} color="blue">
                    <InfoCircleOutlined className="text-gray-300 hover:text-blue-400 cursor-help transition-colors" />
                  </Tooltip>
                </div>
                <div className="flex items-center gap-3">
                  {isRiskFeature && (
                    <Badge status={getRiskColor(key, value)} text={<span className="text-xs text-gray-500 font-medium">{getRiskLevel(key, value)} Risk</span>} />
                  )}
                  <div className="font-mono bg-white border border-gray-200 px-2 py-0.5 rounded-lg text-sm min-w-[3.5rem] text-center shadow-sm font-semibold text-gray-600">
                    {value.toFixed(2)}
                  </div>
                </div>
              </div>
              <Slider 
                min={0} max={1} step={0.01} 
                value={value} 
                onChange={(v) => handleSliderChange(key, v)} 
                trackStyle={{ backgroundColor: colors[key], height: 6 }}
                railStyle={{ height: 6, backgroundColor: '#f0f0f0' }}
                handleStyle={{ borderColor: colors[key], border: 'solid 3px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}
                style={{ margin: '8px 0' }}
              />
            </div>
          );
        })}
      </div>
    </Card>
  );
};
