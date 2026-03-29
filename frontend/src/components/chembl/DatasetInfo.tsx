import React from 'react';
import { Card, Typography } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const DatasetInfo: React.FC = () => {
  return (
    <Card title="Dataset Information" className="h-full">
      <div className="text-center py-8">
        <DatabaseOutlined className="text-4xl text-gray-400 mb-4" />
        <Text type="secondary">No ChEMBL dataset loaded yet</Text>
        <Text className="block mt-4 text-sm">
          Import ChEMBL data to see dataset statistics here.
        </Text>
      </div>
    </Card>
  );
};

export default DatasetInfo;
