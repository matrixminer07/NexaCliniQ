import React, { useState } from 'react';
import { Card, Typography, Input, Button, Space, Select, Alert, Spin, Tag } from 'antd';
import { SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

const ChEMBLImport: React.FC = () => {
  const [targetId, setTargetId] = useState('');
  const [gene, setGene] = useState('');
  const [maxRecords, setMaxRecords] = useState(100);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleImport = async () => {
    if (!targetId.trim() && !gene.trim()) {
      setError('Please enter a target ID or gene name');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const body: any = { max_records: maxRecords };
      if (targetId.trim()) {
        body.target_id = targetId.trim();
      } else if (gene.trim()) {
        body.gene = gene.trim();
      }

      const response = await apiRequest('/data/import-chembl', {
        method: 'POST',
        body: body
      });

      if (response.error) {
        setError(response.error);
      } else {
        setResult(response);
      }
    } catch (err) {
      setError('Failed to import ChEMBL data. Please try again.');
      console.error('ChEMBL import error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Import ChEMBL Data" className="h-full">
      <div className="space-y-4">
        <Space direction="vertical" className="w-full">
          <div>
            <Text strong>Target ID</Text>
            <Input
              placeholder="e.g., CHEMBL203"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="mt-2"
            />
          </div>
          
          <div>
            <Text strong>OR Gene Name</Text>
            <Input
              placeholder="e.g., EGFR"
              value={gene}
              onChange={(e) => setGene(e.target.value)}
              className="mt-2"
            />
          </div>

          <div>
            <Text strong>Max Records</Text>
            <Select
              value={maxRecords}
              onChange={setMaxRecords}
              className="w-full mt-2"
              options={[
                { value: 50, label: '50 records' },
                { value: 100, label: '100 records' },
                { value: 500, label: '500 records' },
                { value: 1000, label: '1000 records' },
                { value: 1500, label: '1500 records' },
              ]}
            />
          </div>

          <Button 
            type="primary" 
            onClick={handleImport}
            loading={loading}
            icon={<DownloadOutlined />}
            size="large"
            className="w-full"
          >
            Import ChEMBL Data
          </Button>
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
            <Text className="block mt-4">Importing ChEMBL data...</Text>
          </div>
        )}

        {result && !loading && (
          <div className="space-y-4 mt-6">
            <div className="bg-green-50 p-4 rounded-lg">
              <Title level={5}>✅ Import Successful</Title>
              <Text>{result.message}</Text>
            </div>

            {result.metrics && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card size="small">
                  <div className="text-center">
                    <Text strong>Training Compounds</Text>
                    <div className="text-2xl font-bold text-blue-600">
                      {result.metrics.n_train}
                    </div>
                  </div>
                </Card>
                <Card size="small">
                  <div className="text-center">
                    <Text strong>Test Compounds</Text>
                    <div className="text-2xl font-bold text-green-600">
                      {result.metrics.n_test}
                    </div>
                  </div>
                </Card>
                <Card size="small">
                  <div className="text-center">
                    <Text strong>CV AUC</Text>
                    <div className="text-2xl font-bold text-purple-600">
                      {result.metrics.cv_auc_mean?.toFixed(3)}
                    </div>
                  </div>
                </Card>
                <Card size="small">
                  <div className="text-center">
                    <Text strong>Data Source</Text>
                    <div className="text-lg">
                      <Tag color="blue">{result.metrics.data_source}</Tag>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};

export default ChEMBLImport;
