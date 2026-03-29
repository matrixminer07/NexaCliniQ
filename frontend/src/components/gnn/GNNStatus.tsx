import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Statistic, Tag, Progress, Alert } from 'antd';
import { RobotOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

const GNNStatus: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await apiRequest('/gnn/status');
        setStatus(response);
      } catch (error) {
        console.error('Failed to fetch GNN status:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  if (loading) {
    return (
      <Card title="GNN Status" className="h-full">
        <div className="text-center py-8">
          <div className="animate-pulse">
            <RobotOutlined className="text-4xl text-gray-400" />
          </div>
          <Text className="block mt-4">Checking GNN status...</Text>
        </div>
      </Card>
    );
  }

  const getStatusIcon = () => {
    if (status?.status === 'trained') {
      return <CheckCircleOutlined className="text-green-600" />;
    } else {
      return <CloseCircleOutlined className="text-orange-600" />;
    }
  };

  const getStatusColor = () => {
    return status?.status === 'trained' ? 'success' : 'warning';
  };

  return (
    <Card title="GNN Status" className="h-full">
      <div className="space-y-4">
        <div className="text-center">
          <div className="mb-4">
            {getStatusIcon()}
          </div>
          <Tag color={getStatusColor()} className="text-lg px-4 py-2">
            {status?.status === 'trained' ? 'Model Trained' : 'Not Trained'}
          </Tag>
        </div>

        {status?.status === 'trained' && status?.best_val_auc && (
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Statistic
                title="Best Validation AUC"
                value={status.best_val_auc}
                precision={3}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="Model Type"
                value="Graph Neural Network"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
          </Row>
        )}

        {status?.status === 'not_trained' && (
          <Alert
            message="GNN Not Trained"
            description="The Graph Neural Network model needs to be trained on molecular data before making predictions."
            type="info"
            showIcon
            className="mt-4"
          />
        )}

        <div className="mt-6 p-4 bg-gray-50 rounded">
          <Title level={5}>Model Information</Title>
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <div>
                <Text strong>Architecture:</Text>
                <div className="mt-2">
                  <Text>Message Passing Neural Network (MPNN)</Text>
                </div>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <Text strong>Layers:</Text>
                <div className="mt-2">
                  <Text>3× GINConv + Global Pooling + MLP</Text>
                </div>
              </div>
            </Col>
          </Row>
          
          <div className="mt-4">
            <Text strong>Input:</Text>
            <div className="mt-2">
              <Text>Molecular graphs from SMILES strings</Text>
            </div>
          </div>
        </div>

        {status?.message && (
          <div className="mt-4">
            <Text type="secondary">{status.message}</Text>
          </div>
        )}
      </div>
    </Card>
  );
};

export default GNNStatus;
