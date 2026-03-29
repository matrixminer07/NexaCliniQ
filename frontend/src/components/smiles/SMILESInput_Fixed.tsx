import React, { useState } from 'react';
import { Input, Button, Card, Typography, Space, Alert, Spin } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

interface SMILESResult {
  success_probability?: number;
  verdict?: string;
  confidence_interval?: any;
  shap_breakdown?: any;
  phase_probabilities?: any;
  model_features?: any;
  raw_descriptors?: any;
  drug_likeness?: any;
  compound_name?: string;
  warnings?: string[];
  error?: string;
}

const SMILESInput: React.FC = () => {
  const [smiles, setSmiles] = useState('');
  const [compoundName, setCompoundName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SMILESResult | null>(null);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!smiles.trim()) {
      setError('Please enter a SMILES string');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await apiRequest('/predict-smiles', {
        method: 'POST',
        body: {
          smiles: smiles.trim(),
          compound_name: compoundName.trim() || undefined
        } as any
      });

      if (response.error) {
        setError(response.error);
      } else {
        setResult(response);
      }
    } catch (err) {
      setError('Failed to process SMILES. Please try again.');
      console.error('SMILES prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (exampleSmiles: string, name: string) => {
    setSmiles(exampleSmiles);
    setCompoundName(name);
  };

  return (
    <div className="space-y-4">
      <Space direction="vertical" className="w-full">
        <div>
          <Text strong>Compound Name (Optional)</Text>
          <Input
            placeholder="e.g., Aspirin"
            value={compoundName}
            onChange={(e) => setCompoundName(e.target.value)}
            className="mt-2"
          />
        </div>
        
        <div>
          <Text strong>SMILES String *</Text>
          <Input.TextArea
            placeholder="e.g., CC(=O)O for Aspirin"
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            rows={3}
            className="mt-2 font-mono text-sm"
          />
        </div>

        <Space className="w-full">
          <Button 
            type="primary" 
            onClick={handleSubmit}
            loading={loading}
            icon={<SendOutlined />}
            size="large"
            className="w-full"
          >
            Analyze Molecule
          </Button>
        </Space>

        <div>
          <Text type="secondary">Examples:</Text>
          <Space wrap className="mt-2">
            <Button 
              size="small" 
              onClick={() => handleExample('CC(=O)O', 'Aspirin')}
            >
              Aspirin
            </Button>
            <Button 
              size="small" 
              onClick={() => handleExample('CC(C)OC1=CC=C(C)C(=O)O', 'Caffeine')}
            >
              Caffeine
            </Button>
            <Button 
              size="small" 
              onClick={() => handleExample('CC(C)CC1=CC=C(C)C(=O)O', 'Ibuprofen')}
            >
              Ibuprofen
            </Button>
          </Space>
        </div>
      </Space>

      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          className="mt-4"
        />
      )}

      {loading && (
        <div className="text-center py-8">
          <Spin size="large" />
          <Text className="block mt-4">Processing molecular structure...</Text>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-4 mt-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <Text strong>Results for {result.compound_name || 'Unknown Compound'}</Text>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card title="Prediction" size="small">
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">
                  {((result.success_probability || 0) * 100).toFixed(1)}%
                </div>
                <Text type="secondary">{result.verdict}</Text>
              </div>
            </Card>

            <Card title="Confidence Interval" size="small">
              <Space direction="vertical" className="w-full">
                <div className="flex justify-between">
                  <Text>P10:</Text>
                  <Text strong>{result.confidence_interval?.p10?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>P50:</Text>
                  <Text strong>{result.confidence_interval?.p50?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>P90:</Text>
                  <Text strong>{result.confidence_interval?.p90?.toFixed(3)}</Text>
                </div>
              </Space>
            </Card>
          </div>

          {result.model_features && (
            <Card title="Model Features" size="small">
              <Space direction="vertical" className="w-full">
                <div className="flex justify-between">
                  <Text>Toxicity:</Text>
                  <Text>{result.model_features.toxicity?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>Bioavailability:</Text>
                  <Text>{result.model_features.bioavailability?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>Solubility:</Text>
                  <Text>{result.model_features.solubility?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>Binding:</Text>
                  <Text>{result.model_features.binding?.toFixed(3)}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>Molecular Weight:</Text>
                  <Text>{result.model_features.molecular_weight?.toFixed(3)}</Text>
                </div>
              </Space>
            </Card>
          )}

          {result.drug_likeness && (
            <Card title="Drug Likeness" size="small">
              <Space direction="vertical" className="w-full">
                <div className="flex justify-between">
                  <Text>Overall:</Text>
                  <Text strong className={result.drug_likeness.overall === 'Excellent' ? 'text-green-600' : 'text-yellow-600'}>
                    {result.drug_likeness.overall}
                  </Text>
                </div>
                <div className="flex justify-between">
                  <Text>Lipinski:</Text>
                  <Text>{result.drug_likeness.lipinski_pass ? '✅ Pass' : '❌ Fail'}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>Veber:</Text>
                  <Text>{result.drug_likeness.veber_pass ? '✅ Pass' : '❌ Fail'}</Text>
                </div>
                <div className="flex justify-between">
                  <Text>QED Score:</Text>
                  <Text>{result.drug_likeness.qed_score?.toFixed(3)}</Text>
                </div>
              </Space>
            </Card>
          )}

          {result.warnings && result.warnings.length > 0 && (
            <Alert
              message="Warnings"
              description={
                <ul>
                  {result.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              }
              type="warning"
              showIcon
              className="mt-4"
            />
          )}
        </div>
      )}
    </div>
  );
};

export default SMILESInput;
