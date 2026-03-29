import React from 'react';
import { Card, Typography, Row, Col, Statistic } from 'antd';
import { SettingOutlined } from '@ant-design/icons';

const { Title } = Typography;

const ModelStats: React.FC = () => {
  return (
    <Card title="Model Statistics" className="h-full">
      <div className="space-y-4">
        <Title level={5}>Platform Overview</Title>
        
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic
              title="Total Predictions"
              value={1247}
              prefix={<SettingOutlined />}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Success Rate"
              value={68.3}
              precision={1}
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Avg Confidence"
              value={0.82}
              precision={2}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Models Active"
              value={8}
              prefix={<SettingOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
        </Row>

        <div className="mt-6 p-4 bg-gray-50 rounded">
          <Title level={5}>Active Models</Title>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-blue-600 mb-2" />
              <div>Random Forest</div>
            </div>
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-green-600 mb-2" />
              <div>SMILES Pipeline</div>
            </div>
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-purple-600 mb-2" />
              <div>Therapeutic Models</div>
            </div>
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-orange-600 mb-2" />
              <div>Risk Analytics</div>
            </div>
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-red-600 mb-2" />
              <div>Scenario Engine</div>
            </div>
            <div className="text-center p-3 bg-white rounded">
              <SettingOutlined className="text-2xl text-cyan-600 mb-2" />
              <div>Graph Neural Network</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default ModelStats;
