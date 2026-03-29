import React, { useState } from 'react';
import { Card, Typography, Input, Button, Space, Alert, Tag } from 'antd';
import { RobotOutlined, SendOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

interface GNNResult {
  compound_name?: string;
  success_probability?: number;
  verdict?: string;
  confidence_interval?: {
    p10?: number;
    p50?: number;
    p90?: number;
  };
  model_used?: string;
  fallback?: boolean;
  error?: string;
}

const GNNPrediction: React.FC = () => {
  const [smiles, setSmiles] = useState('');
  const [compoundName, setCompoundName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GNNResult | null>(null);
  const [error, setError] = useState('');

  const handlePredict = async () => {
    if (!smiles.trim()) {
      setError('Please enter a SMILES string');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await apiRequest('/predict-gnn', {
        method: 'POST',
        body: {
          smiles: smiles.trim(),
          compound_name: compoundName.trim() || undefined
        }
      });

      if (response.error) {
        setError(response.error);
      } else {
        setResult(response);
      }
    } catch (err) {
      setError('Failed to process GNN prediction. Please try again.');
      console.error('GNN prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExample = (exampleSmiles: string, name: string) => {
    setSmiles(exampleSmiles);
    setCompoundName(name);
  };

  return (
    <Card title="GNN Prediction" className="h-full">
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

          <Button 
            type="primary" 
            onClick={handlePredict}
            loading={loading}
            icon={<SendOutlined />}
            size="large"
            className="w-full"
          >
            Predict with GNN
          </Button>

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
                onClick={() => handleExample('c1cc2c(c1)O', 'Caffeine')}
              >
                Caffeine
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
            <div className="animate-pulse">
              <RobotOutlined className="text-4xl text-blue-600 mb-4" />
            </div>
            <Text>Processing molecular graph...</Text>
          </div>
        )}

        {result && !loading && (
          <div className="space-y-4 mt-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <Text strong>GNN Results for {result.compound_name || 'Unknown Compound'}</Text>
            </div>

            {result.fallback && (
              <Alert
                message="Using Fallback Model"
                description="The GNN model is not trained yet. Using Random Forest model instead."
                type="warning"
                showIcon
                className="mb-4"
              />
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-1">
                <Card size="small">
                  <div className="text-center">
                    <Text strong>Success Probability</Text>
                    <div className="text-3xl font-bold text-blue-600 mt-2">
                      {((result.success_probability || 0) * 100).toFixed(1)}%
                    </div>
                    <Text type="secondary">{result.verdict}</Text>
                  </div>
                </Card>
              </div>
              <div className="md:col-span-1">
                <Card size="small">
                  <div className="text-center">
                    <Text strong>Model Used</Text>
                    <div className="mt-2">
                      <Tag color={result.fallback ? 'orange' : 'green'} className="text-lg px-4 py-2">
                        {result.model_used}
                      </Tag>
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            {result.model_used === 'graph_neural_network' && result.confidence_interval && (
              <Card size="small" className="mt-4">
                <Title level={5}>Confidence Interval</Title>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <Text className="text-xs">P10</Text>
                    <div className="text-lg font-bold">
                      {result.confidence_interval.p10?.toFixed(3)}
                    </div>
                  </div>
                  <div className="text-center">
                    <Text className="text-xs">P50</Text>
                    <div className="text-lg font-bold">
                      {result.confidence_interval.p50?.toFixed(3)}
                    </div>
                  </div>
                  <div className="text-center">
                    <Text className="text-xs">P90</Text>
                    <div className="text-lg font-bold">
                      {result.confidence_interval.p90?.toFixed(3)}
                    </div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};

export default GNNPrediction;
