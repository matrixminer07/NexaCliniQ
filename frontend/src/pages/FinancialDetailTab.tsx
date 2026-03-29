import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spin, Empty, Collapse, Table, Tag, Statistic, Tooltip } from 'antd';
import { DollarOutlined, LineChartOutlined, CalendarOutlined } from '@ant-design/icons';
import { api } from '../services/api';

interface CapexDetail {
  [key: string]: any;
  year_1?: number;
  year_2?: number;
  year_3?: number;
  year_4?: number;
  category_total?: number;
  description?: string;
}

interface OpexFunction {
  [key: string]: any;
  headcount_year1?: number;
  headcount_year5?: number;
  salary_burden_per_person_musd?: number;
  description?: string;
  year_1_opex?: number;
  year_2_opex?: number;
  year_3_opex?: number;
  year_5_opex?: number;
}

interface CashflowYear {
  capex: number;
  opex: number;
  revenue: number;
  net_cashflow: number;
}

interface FinancialOutcome {
  cumulative_capex_musd: number;
  cumulative_opex_musd: number;
  cumulative_revenue_musd: number;
  net_cumulative_cashflow_musd: number;
  npv_at_10pct_discount_musd: number;
  irr_pct: number;
  payback_year: number;
}

interface FinancialDetail {
  option_id: string;
  option_name: string;
  total_capex_musd: number;
  capex_breakdown: Record<string, CapexDetail>;
  opex_by_function: Record<string, OpexFunction>;
  annual_cashflow: Record<string, CashflowYear>;
  financial_outcomes_5yr: FinancialOutcome;
  sensitivity_tornado?: {
    base_npv_musd: number;
    variables: Record<string, any>;
    top_driver: string;
  };
}

export const FinancialDetailTab: React.FC = () => {
  const [data, setData] = useState<Record<string, FinancialDetail> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.financialDetail();
        setData(((response?.by_option as unknown) as Record<string, FinancialDetail>) || null);
        setSelectedOption('ai_platform');
      } catch (err: any) {
        setError(err?.message || 'Failed to fetch financial details');
        console.error('Financial detail fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '50px' }} />;
  if (error) return <Card>{error}</Card>;
  if (!data) return <Empty />;

  const selected = selectedOption && data[selectedOption];
  if (!selected) return <Empty />;

  const optionTabs = [
    { key: 'ai_platform', label: 'AI Platform (₹230M, 28.5% IRR)' },
    { key: 'biologics_expansion', label: 'Biologics (₹190M, 19.2% IRR)' },
    { key: 'traditional_portfolio', label: 'Traditional (₹160M, 14.8% IRR)' },
  ];

  const capexColumns = [
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: 'Y1',
      dataIndex: 'y1',
      key: 'y1',
      render: (val: number) => `₹${val}M`,
    },
    {
      title: 'Y2',
      dataIndex: 'y2',
      key: 'y2',
      render: (val: number) => `₹${val}M`,
    },
    {
      title: 'Y3',
      dataIndex: 'y3',
      key: 'y3',
      render: (val: number) => `₹${val}M`,
    },
    {
      title: 'Y4',
      dataIndex: 'y4',
      key: 'y4',
      render: (val: number) => `₹${val}M`,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      render: (val: number) => <strong>₹{val}M</strong>,
    },
  ];

  const capexData = Object.entries(selected.capex_breakdown || {}).map(([cat, details]) => ({
    key: cat,
    category: cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    y1: details.year_1 || 0,
    y2: details.year_2 || 0,
    y3: details.year_3 || 0,
    y4: details.year_4 || 0,
    total: (details as any).category_total || 0,
  }));

  const opexColumns = [
    { title: 'Function', dataIndex: 'function', key: 'function' },
    { title: 'Y1 (M₹)', dataIndex: 'y1_opex', key: 'y1_opex', render: (v: number) => `₹${v.toFixed(2)}M` },
    { title: 'Y2 (M₹)', dataIndex: 'y2_opex', key: 'y2_opex', render: (v: number) => `₹${v.toFixed(2)}M` },
    { title: 'Y3 (M₹)', dataIndex: 'y3_opex', key: 'y3_opex', render: (v: number) => `₹${v.toFixed(2)}M` },
    { title: 'Y5 (M₹)', dataIndex: 'y5_opex', key: 'y5_opex', render: (v: number) => `₹${v.toFixed(2)}M` },
  ];

  const opexData = Object.entries(selected.opex_by_function || {}).map(([func, details]) => ({
    key: func,
    function: func.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    y1_opex: (details as any).year_1_opex || 0,
    y2_opex: (details as any).year_2_opex || 0,
    y3_opex: (details as any).year_3_opex || 0,
    y5_opex: (details as any).year_5_opex || 0,
  }));

  const outcomes = selected.financial_outcomes_5yr || {};

  return (
    <div style={{ padding: '20px' }}>
      <Card title={<h2>💰 Financial Detail Analysis</h2>} style={{ marginBottom: '20px' }}>
        <div className="space-y-4">
          <div>
            <h3 style={{ marginBottom: '10px' }}>Select Strategy Option</h3>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {optionTabs.map(tab => (
                <button
                  key={tab.key}
                  className={`px-4 py-2 rounded cursor-pointer transition ${
                    selectedOption === tab.key
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                  onClick={() => setSelectedOption(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Key Financial Metrics */}
      <Card title="5-Year Financial Outcomes" style={{ marginBottom: '20px' }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8}>
            <Statistic
              title="NPV @ 10% Discount"
              value={outcomes.npv_at_10pct_discount_musd}
              prefix="₹"
              suffix="M"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="IRR"
              value={outcomes.irr_pct?.toFixed(1) || 0}
              suffix="%"
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="Payback Year"
              value={outcomes.payback_year?.toFixed(1) || 0}
              prefix="~Yr "
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Total Capex"
              value={selected.total_capex_musd}
              prefix="₹"
              suffix="M"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Cumulative Revenue (5yr)"
              value={(outcomes.cumulative_revenue_musd || 0).toFixed(1)}
              prefix="₹"
              suffix="M"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Cumulative Opex (5yr)"
              value={(outcomes.cumulative_opex_musd || 0).toFixed(1)}
              prefix="₹"
              suffix="M"
            />
          </Col>
        </Row>
      </Card>

      {/* Capex Breakdown */}
      <Card 
        title={<><DollarOutlined /> Capex Breakdown by Category</>}
        style={{ marginBottom: '20px' }}
        size="small"
      >
        <Table
          columns={capexColumns}
          dataSource={capexData}
          pagination={false}
          size="small"
        />
      </Card>

      {/* Opex by Function */}
      <Card 
        title={<><LineChartOutlined /> Operating Costs by Function (First 5 Years)</>}
        style={{ marginBottom: '20px' }}
        size="small"
      >
        <Table
          columns={opexColumns}
          dataSource={opexData}
          pagination={false}
          size="small"
        />
      </Card>

      {/* Annual Cashflow Waterfall */}
      <Card 
        title={<><CalendarOutlined /> Annual Cashflow Waterfall</>}
        style={{ marginBottom: '20px' }}
        size="small"
      >
        <Table
          columns={[
            { title: 'Year', dataIndex: 'year', key: 'year' },
            { title: 'Capex', dataIndex: 'capex', key: 'capex', render: (v: number) => <span style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>₹{v}M</span> },
            { title: 'Opex', dataIndex: 'opex', key: 'opex', render: (v: number) => <span style={{ color: '#ff4d4f' }}>₹{v}M</span> },
            { title: 'Revenue', dataIndex: 'revenue', key: 'revenue', render: (v: number) => <span style={{ color: '#52c41a' }}>₹{v}M</span> },
            { title: 'Net Cashflow', dataIndex: 'net_cashflow', key: 'net_cashflow', render: (v: number) => (
              <strong style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>₹{v}M</strong>
            )},
          ]}
          dataSource={Object.entries(selected.annual_cashflow || {}).map(([yr, details], idx) => ({
            key: yr,
            year: `Year ${idx + 1}`,
            capex: details.capex,
            opex: -details.opex,
            revenue: details.revenue,
            net_cashflow: details.net_cashflow,
          }))}
          pagination={false}
          size="small"
        />
      </Card>

      {/* Sensitivity Analysis */}
      {selected.sensitivity_tornado && (
        <Card 
          title="📊 Sensitivity Analysis (Tornado)"
          style={{ marginBottom: '20px' }}
          size="small"
        >
          <p><strong>Top Driver:</strong> {selected.sensitivity_tornado.top_driver}</p>
          <Table
            columns={[
              { title: 'Variable', dataIndex: 'variable', key: 'variable' },
              { title: 'Downside NPV', dataIndex: 'downside', key: 'downside', render: (v: number) => `₹${v}M` },
              { title: 'Upside NPV', dataIndex: 'upside', key: 'upside', render: (v: number) => `₹${v}M` },
              { title: 'Sensitivity', dataIndex: 'sensitivity', key: 'sensitivity', render: (v: number) => `${v}%` },
            ]}
            dataSource={Object.entries(selected.sensitivity_tornado.variables || {}).map(([v, details]) => ({
              key: v,
              variable: v.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
              downside: (details.impact_range_musd?.[0] || 0),
              upside: (details.impact_range_musd?.[1] || 0),
              sensitivity: details.sensitivity_pct_per_10pct || 0,
            }))}
            pagination={false}
            size="small"
          />
        </Card>
      )}
    </div>
  );
};

export default FinancialDetailTab;
