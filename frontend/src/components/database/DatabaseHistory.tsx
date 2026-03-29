import React, { useEffect, useState } from 'react';
import { Card, Typography, Table, Tag } from 'antd';
import { apiGet } from '../../utils/api';

const { Title } = Typography;

const DatabaseHistory: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const results = await apiGet('/history?limit=50');
        setData((Array.isArray(results) ? results : []).map((r: any, i: number) => ({
          key: r.id || `row-${i}`,
          timestamp: r.timestamp || '',
          compound_name: r.compound_name || 'Unknown',
          input_type: r.smiles ? 'smiles' : 'sliders',
          smiles: r.smiles,
          success_probability: r.probability ?? 0,
          verdict: r.verdict || 'N/A',
        })));
      } catch (err) {
        console.error('Failed to load history:', err);
        setData([]);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
    },
    {
      title: 'Compound',
      dataIndex: 'compound_name',
      key: 'compound',
    },
    {
      title: 'Input Type',
      dataIndex: 'input_type',
      key: 'input_type',
      render: (type: string) => (
        <Tag color={type === 'smiles' ? 'blue' : 'green'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Success Probability',
      dataIndex: 'success_probability',
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
    <Card title="Prediction History" className="h-full">
      <div className="space-y-4">
        <Title level={5}>Recent Predictions</Title>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </div>
    </Card>
  );
};

export default DatabaseHistory;
