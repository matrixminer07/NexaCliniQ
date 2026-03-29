import React, { useState, useEffect } from 'react';
import { Card, Typography, Row, Col, Tag, Progress, Statistic } from 'antd';
import { MedicineBoxOutlined } from '@ant-design/icons';
import { apiRequest } from '../../utils/api';

const { Title, Text } = Typography;

interface TherapeuticArea {
  name: string;
  description: string;
  color: string;
  attrition_rates: {
    phase1: number;
    phase2: number;
    phase3: number;
  };
}

const TherapeuticAreas: React.FC = () => {
  const [areas, setAreas] = useState<Record<string, TherapeuticArea>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTherapeuticAreas = async () => {
      try {
        const response = await apiRequest('/therapeutic-areas');
        if (response.therapeutic_areas) {
          setAreas(response.therapeutic_areas);
        }
      } catch (error) {
        console.error('Failed to fetch therapeutic areas:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTherapeuticAreas();
  }, []);

  if (loading) {
    return (
      <Card title="Therapeutic Areas" className="h-full">
        <div className="text-center py-8">
          <div className="animate-pulse">
            <MedicineBoxOutlined className="text-4xl text-gray-400" />
          </div>
          <Text className="block mt-4">Loading therapeutic areas...</Text>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Therapeutic Areas" className="h-full">
      <div className="space-y-4">
        <Text className="mb-4">
          Specialized models for different therapeutic indications with tailored attrition rates and feature weights.
        </Text>
        
        <div className="space-y-3">
          {Object.entries(areas).map(([key, area]) => (
            <Card 
              key={key}
              size="small"
              className="border-l-4"
              style={{ borderLeftColor: area.color }}
            >
              <div className="flex justify-between items-start mb-3">
                <Title level={5} className="!mb-0">
                  {area.name}
                </Title>
                <Tag color={area.color}>{key}</Tag>
              </div>
              
              <Text type="secondary" className="text-sm mb-4">
                {area.description}
              </Text>

              <div className="space-y-2">
                <div>
                  <Text strong>Phase Attrition Rates:</Text>
                  <Row gutter={[8, 8]} className="mt-2">
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-xs">Phase I</Text>
                        <Progress 
                          percent={(1 - area.attrition_rates.phase1) * 100} 
                          size="small"
                          status="active"
                          strokeColor="#52c41a"
                        />
                        <Text className="text-xs">{((1 - area.attrition_rates.phase1) * 100).toFixed(1)}% success</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-xs">Phase II</Text>
                        <Progress 
                          percent={(1 - area.attrition_rates.phase2) * 100} 
                          size="small"
                          status="active"
                          strokeColor="#faad14"
                        />
                        <Text className="text-xs">{((1 - area.attrition_rates.phase2) * 100).toFixed(1)}% success</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-xs">Phase III</Text>
                        <Progress 
                          percent={(1 - area.attrition_rates.phase3) * 100} 
                          size="small"
                          status="active"
                          strokeColor="#f59e0b"
                        />
                        <Text className="text-xs">{((1 - area.attrition_rates.phase3) * 100).toFixed(1)}% success</Text>
                      </div>
                    </Col>
                  </Row>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default TherapeuticAreas;
