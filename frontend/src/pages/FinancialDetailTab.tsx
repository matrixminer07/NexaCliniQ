import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spin, Empty, Collapse, Table, Tag, Statistic, Tooltip } from 'antd';
import { DollarOutlined, LineChartOutlined, CalendarOutlined } from '@ant-design/icons';
import { api } from '../services/api';
import { formatMillions } from '@/utils/numberFormat';

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

const FALLBACK_FINANCIAL_DETAILS: Record<string, FinancialDetail> = {
  ai_platform: {
    option_id: 'ai_platform',
    option_name: 'AI Platform',
    total_capex_musd: 230,
    capex_breakdown: {
      platform_build: { year_1: 70, year_2: 45, year_3: 20, year_4: 5, category_total: 140 },
      data_and_compute: { year_1: 18, year_2: 16, year_3: 14, year_4: 8, category_total: 56 },
      regulatory_and_ops: { year_1: 8, year_2: 10, year_3: 9, year_4: 7, category_total: 34 },
    },
    opex_by_function: {
      research: { year_1_opex: 12, year_2_opex: 16, year_3_opex: 19, year_5_opex: 25 },
      cloud_ops: { year_1_opex: 7, year_2_opex: 9, year_3_opex: 11, year_5_opex: 13 },
      commercial: { year_1_opex: 5, year_2_opex: 8, year_3_opex: 12, year_5_opex: 15 },
    },
    annual_cashflow: {
      y1: { capex: -96, opex: 24, revenue: 20, net_cashflow: -100 },
      y2: { capex: -71, opex: 33, revenue: 48, net_cashflow: -56 },
      y3: { capex: -43, opex: 42, revenue: 96, net_cashflow: 11 },
      y4: { capex: -20, opex: 48, revenue: 165, net_cashflow: 97 },
      y5: { capex: 0, opex: 53, revenue: 238, net_cashflow: 185 },
    },
    financial_outcomes_5yr: {
      cumulative_capex_musd: 230,
      cumulative_opex_musd: 200,
      cumulative_revenue_musd: 567,
      net_cumulative_cashflow_musd: 137,
      npv_at_10pct_discount_musd: 214,
      irr_pct: 28.5,
      payback_year: 3.2,
    },
    sensitivity_tornado: {
      base_npv_musd: 214,
      top_driver: 'Platform ARR growth',
      variables: {
        platform_arr_growth: { impact_range_musd: [165, 268], sensitivity_pct_per_10pct: 19 },
        clinical_timeline: { impact_range_musd: [182, 244], sensitivity_pct_per_10pct: 11 },
      },
    },
  },
  biologics_expansion: {
    option_id: 'biologics_expansion',
    option_name: 'Biologics Expansion',
    total_capex_musd: 190,
    capex_breakdown: {
      wet_lab_scale: { year_1: 52, year_2: 36, year_3: 18, year_4: 4, category_total: 110 },
      manufacturing: { year_1: 22, year_2: 19, year_3: 13, year_4: 7, category_total: 61 },
      quality_systems: { year_1: 4, year_2: 5, year_3: 6, year_4: 4, category_total: 19 },
    },
    opex_by_function: {
      research: { year_1_opex: 11, year_2_opex: 14, year_3_opex: 17, year_5_opex: 21 },
      operations: { year_1_opex: 8, year_2_opex: 10, year_3_opex: 12, year_5_opex: 14 },
      commercial: { year_1_opex: 4, year_2_opex: 6, year_3_opex: 8, year_5_opex: 11 },
    },
    annual_cashflow: {
      y1: { capex: -78, opex: 23, revenue: 15, net_cashflow: -86 },
      y2: { capex: -60, opex: 30, revenue: 34, net_cashflow: -56 },
      y3: { capex: -37, opex: 37, revenue: 74, net_cashflow: 0 },
      y4: { capex: -15, opex: 43, revenue: 121, net_cashflow: 63 },
      y5: { capex: 0, opex: 46, revenue: 171, net_cashflow: 125 },
    },
    financial_outcomes_5yr: {
      cumulative_capex_musd: 190,
      cumulative_opex_musd: 179,
      cumulative_revenue_musd: 415,
      net_cumulative_cashflow_musd: 46,
      npv_at_10pct_discount_musd: 142,
      irr_pct: 19.2,
      payback_year: 4.0,
    },
  },
  traditional_portfolio: {
    option_id: 'traditional_portfolio',
    option_name: 'Traditional Portfolio',
    total_capex_musd: 160,
    capex_breakdown: {
      program_expansion: { year_1: 41, year_2: 31, year_3: 20, year_4: 8, category_total: 100 },
      trial_enablement: { year_1: 19, year_2: 14, year_3: 10, year_4: 6, category_total: 49 },
      governance: { year_1: 3, year_2: 3, year_3: 3, year_4: 2, category_total: 11 },
    },
    opex_by_function: {
      research: { year_1_opex: 10, year_2_opex: 12, year_3_opex: 14, year_5_opex: 17 },
      operations: { year_1_opex: 7, year_2_opex: 8, year_3_opex: 10, year_5_opex: 12 },
      commercial: { year_1_opex: 3, year_2_opex: 5, year_3_opex: 7, year_5_opex: 8 },
    },
    annual_cashflow: {
      y1: { capex: -63, opex: 20, revenue: 12, net_cashflow: -71 },
      y2: { capex: -48, opex: 25, revenue: 24, net_cashflow: -49 },
      y3: { capex: -33, opex: 31, revenue: 49, net_cashflow: -15 },
      y4: { capex: -16, opex: 36, revenue: 81, net_cashflow: 29 },
      y5: { capex: 0, opex: 37, revenue: 116, net_cashflow: 79 },
    },
    financial_outcomes_5yr: {
      cumulative_capex_musd: 160,
      cumulative_opex_musd: 149,
      cumulative_revenue_musd: 282,
      net_cumulative_cashflow_musd: -27,
      npv_at_10pct_discount_musd: 96,
      irr_pct: 14.8,
      payback_year: 4.7,
    },
  },
}

function normalizeFinancialDetailPayload(response: any): Record<string, FinancialDetail> {
  const byOption = response?.by_option
  if (byOption && typeof byOption === 'object' && Object.keys(byOption).length > 0) {
    return byOption as Record<string, FinancialDetail>
  }

  const legacy = response?.financial_detail
  if (legacy && typeof legacy === 'object' && Object.keys(legacy).length > 0) {
    return legacy as Record<string, FinancialDetail>
  }

  return FALLBACK_FINANCIAL_DETAILS
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
        setError(null);
        const response = await api.financialDetail();
        const normalized = normalizeFinancialDetailPayload(response);
        setData(normalized);
        setSelectedOption(Object.keys(normalized)[0] || 'ai_platform');
      } catch (err: any) {
        setData(FALLBACK_FINANCIAL_DETAILS);
        setSelectedOption('ai_platform');
        setError('Using fallback financial detail data.');
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
    { key: 'ai_platform', label: 'AI Platform (230M, 28.5% IRR)' },
    { key: 'biologics_expansion', label: 'Biologics (190M, 19.2% IRR)' },
    { key: 'traditional_portfolio', label: 'Traditional (160M, 14.8% IRR)' },
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
      render: (val: number) => formatMillions(val),
    },
    {
      title: 'Y2',
      dataIndex: 'y2',
      key: 'y2',
      render: (val: number) => formatMillions(val),
    },
    {
      title: 'Y3',
      dataIndex: 'y3',
      key: 'y3',
      render: (val: number) => formatMillions(val),
    },
    {
      title: 'Y4',
      dataIndex: 'y4',
      key: 'y4',
      render: (val: number) => formatMillions(val),
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      render: (val: number) => <strong>{formatMillions(val)}</strong>,
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
    { title: 'Y1 (Million)', dataIndex: 'y1_opex', key: 'y1_opex', render: (v: number) => formatMillions(v, 2) },
    { title: 'Y2 (Million)', dataIndex: 'y2_opex', key: 'y2_opex', render: (v: number) => formatMillions(v, 2) },
    { title: 'Y3 (Million)', dataIndex: 'y3_opex', key: 'y3_opex', render: (v: number) => formatMillions(v, 2) },
    { title: 'Y5 (Million)', dataIndex: 'y5_opex', key: 'y5_opex', render: (v: number) => formatMillions(v, 2) },
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
              suffix="M"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Cumulative Revenue (5yr)"
              value={(outcomes.cumulative_revenue_musd || 0).toFixed(1)}
              suffix="M"
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="Cumulative Opex (5yr)"
              value={(outcomes.cumulative_opex_musd || 0).toFixed(1)}
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
            { title: 'Capex', dataIndex: 'capex', key: 'capex', render: (v: number) => <span style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>{formatMillions(v)}</span> },
            { title: 'Opex', dataIndex: 'opex', key: 'opex', render: (v: number) => <span style={{ color: '#ff4d4f' }}>{formatMillions(v)}</span> },
            { title: 'Revenue', dataIndex: 'revenue', key: 'revenue', render: (v: number) => <span style={{ color: '#52c41a' }}>{formatMillions(v)}</span> },
            { title: 'Net Cashflow', dataIndex: 'net_cashflow', key: 'net_cashflow', render: (v: number) => (
              <strong style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>{formatMillions(v)}</strong>
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
              { title: 'Downside NPV', dataIndex: 'downside', key: 'downside', render: (v: number) => formatMillions(v) },
              { title: 'Upside NPV', dataIndex: 'upside', key: 'upside', render: (v: number) => formatMillions(v) },
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
