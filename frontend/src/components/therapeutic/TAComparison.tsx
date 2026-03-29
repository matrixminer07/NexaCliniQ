import React, { useState } from 'react';
import { Card, Typography, Row, Col, Button, Input, Space, Table, Tag } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

interface TAComparisonProps {}

const TAComparison: React.FC<TAComparisonProps> = () => {
  const [features, setFeatures] = useState([0.3, 0.7, 0.6, 0.8, 0.5]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleCompare = async () => {
    setLoading(true);
    try {
      const response = await apiRequest('/predict-ta', {
        method: 'POST',
        body: {
          features, compare_all: true
        } as any
      });setResults(response);
    } catch (error) {
      console.error('TA comparison failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const featureNames = ['Toxicity', 'Bioavailability', 'Solubility', 'Binding', 'Molecular Weight'];
  
  const columns = [
    {
      title: 'Therapeutic Area',
      dataIndex: 'therapeutic_area',
      key: 'area',
    },
    {
      title: 'Success Probability',
      dataIndex: 'probability',
      key: 'probability',
      render: (prob: number) => `${(prob * 100).toFixed(1)}%`,
    },
    {
      title: 'Verdict',
      dataIndex: 'verdict',
      key: 'verdict',
    },
  ];

  return (
    <Card title="Cross-Therapeutic Area Comparison" className="h-full">
      <div className="space-y-4">
        <div>
          <Title level={5}>Input Features</Title>
          <Row gutter={[16, 16]} className="mt-4">
            {features.map((value, index) => (
              <Col xs={12} sm={8} md={4} key={index}>
                <div className="space-y-2">
                  <Text className="text-sm">{featureNames[index]}</Text>
                  <Input
                    type="number"
                    value={value}
                    onChange={(e) => {
                      const newFeatures = [...features];
                      newFeatures[index] = parseFloat(e.target.value) || 0;
                      setFeatures(newFeatures);
                    }}
                    min={0}
                    max={1}
                    step={0.1}
                  />
                </div>
              </Col>
            ))}
          </Row>
          
          <div className="mt-4">
            <Button 
              type="primary" 
              onClick={handleCompare}
              loading={loading}
              icon={<BarChartOutlined />}
              size="large"
              className="w-full"
            >
              Compare All Therapeutic Areas
            </Button>
          </div>
        </div>

        {results && results.comparison && (
          <div className="mt-6">
            <Title level={5}>Comparison Results</Title>
            <Table
              columns={columns}
              dataSource={results.comparison}
              pagination={false}
              size="small"
              rowKey="therapeutic_area"
            />
            
            <div className="mt-4 p-4 bg-gray-50 rounded">
              <Title level={5}>Best Match</Title>
              <div className="flex items-center gap-4">
                <Tag color="green">
                  {results.best_match?.therapeutic_area}
                </Tag>
                <div>
                  <Text strong>Success Probability: </Text>
                  <Text className="text-green-600 text-lg">
                    {((results.best_match?.probability || 0) * 100).toFixed(1)}%
                  </Text>
                </div>
              </div>
              <div className="mt-2">
                <Text type="secondary">
                  {results.best_match?.verdict}
                </Text>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

export default TAComparison;
