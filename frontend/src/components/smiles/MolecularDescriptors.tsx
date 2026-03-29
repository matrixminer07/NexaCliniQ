import React from 'react';
import { Card, Typography, Row, Col, Statistic, Progress } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface MolecularDescriptorsProps {
  descriptors?: {
    molecular_weight?: number;
    logp?: number;
    hbd?: number;
    hba?: number;
    rotatable_bonds?: number;
    tpsa?: number;
    solubility?: number;
    permeability?: number;
    bioavailability?: number;
  };
  admet?: {
    solubility?: string;
    permeability?: string;
    bioavailability?: string;
    toxicity?: string;
  };
}

export const MolecularDescriptors: React.FC<MolecularDescriptorsProps> = ({ descriptors, admet }) => {
  if (!descriptors) {
    return (
      <Card title="Molecular Descriptors">
        <div className="text-center py-8">
          <ExperimentOutlined className="text-4xl text-gray-400 mb-4" />
          <Text type="secondary">No molecular data available</Text>
        </div>
      </Card>
    );
  }

  const getLogPColor = (logp: number) => {
    if (logp < 0) return '#52c41a';
    if (logp < 1) return '#fadb14';
    if (logp < 2) return '#f59e0b';
    if (logp < 3) return '#fa8c16';
    return '#dc3545';
  };

  const getTPSAColor = (tpsa: number) => {
    if (tpsa < 40) return '#52c41a';
    if (tpsa < 70) return '#fadb14';
    if (tpsa < 100) return '#f59e0b';
    if (tpsa < 140) return '#fa8c16';
    return '#dc3545';
  };

  return (
    <Card title="Molecular Descriptors" className="h-full">
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <Statistic
            title="Molecular Weight"
            value={descriptors.molecular_weight?.toFixed(2)}
            suffix="Da"
            precision={2}
          />
        </Col>
        <Col xs={12} sm={8}>
          <Statistic
            title="LogP"
            value={descriptors.logp?.toFixed(2)}
            precision={2}
            valueStyle={{ color: getLogPColor(descriptors.logp || 0) }}
          />
        </Col>
        <Col xs={12} sm={8}>
          <Statistic
            title="H-Bond Donors"
            value={descriptors.hbd}
            precision={0}
          />
        </Col>
        <Col xs={12} sm={8}>
          <Statistic
            title="H-Bond Acceptors"
            value={descriptors.hba}
            precision={0}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="mt-4">
        <Col xs={12} sm={8}>
          <div>
            <Text>Topological Polar Surface Area</Text>
            <Progress
              percent={Math.min(100, (descriptors.tpsa || 0) / 1.4)}
              strokeColor={getTPSAColor(descriptors.tpsa || 0)}
              className="mt-2"
            />
            <Text type="secondary" className="text-xs mt-1">
              {descriptors.tpsa?.toFixed(1)} Ų
            </Text>
          </div>
        </Col>
        <Col xs={12} sm={8}>
          <div>
            <Text>Rotatable Bonds</Text>
            <Progress
              percent={Math.min(100, (descriptors.rotatable_bonds || 0) * 10)}
              className="mt-2"
            />
            <Text type="secondary" className="text-xs mt-1">
              {descriptors.rotatable_bonds} bonds
            </Text>
          </div>
        </Col>
      </Row>

      {admet && (
        <div className="mt-6">
          <Title level={5}>ADMET Predictions</Title>
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Card size="small">
                <div className="text-center">
                  <Text strong>Solubility</Text>
                  <div className="mt-2">
                    <Text className={`text-lg ${
                      admet.solubility === 'High' ? 'text-green-600' :
                      admet.solubility === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {admet.solubility || 'Unknown'}
                    </Text>
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <div className="text-center">
                  <Text strong>Permeability</Text>
                  <div className="mt-2">
                    <Text className={`text-lg ${
                      admet.permeability === 'High' ? 'text-green-600' :
                      admet.permeability === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {admet.permeability || 'Unknown'}
                    </Text>
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <div className="text-center">
                  <Text strong>Bioavailability</Text>
                  <div className="mt-2">
                    <Text className={`text-lg ${
                      admet.bioavailability === 'High' ? 'text-green-600' :
                      admet.bioavailability === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {admet.bioavailability || 'Unknown'}
                    </Text>
                  </div>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small">
                <div className="text-center">
                  <Text strong>Toxicity Risk</Text>
                  <div className="mt-2">
                    <Text className={`text-lg ${
                      admet.toxicity === 'Low' ? 'text-green-600' :
                      admet.toxicity === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {admet.toxicity || 'Unknown'}
                    </Text>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>
        </div>
      )}
    </Card>
  );
};


