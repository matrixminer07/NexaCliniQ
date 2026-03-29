"""
Executive Summary Engine for PharmaNeXus
Assembles board-ready recommendation with evidence, key metrics, risks, and next steps
"""

from typing import Dict, List, Any

def get_executive_summary() -> Dict[str, Any]:
    """
    Return board-ready executive summary with recommendation, scorecard, evidence, risks, and next steps
    """
    
    return {
        "recommendation": {
            "primary_choice": "ai_platform",
            "recommendation_statement": "NovaCura should pursue the AI-Driven Drug Discovery Platform as its primary strategy, staged with strategic partnerships over 4 years. This option maximizes long-term shareholder value ($980M NPV, 28.5% IRR) while establishing defensible competitive moats in the fastest-growing pharma tech market segment.",
            "confidence_level_pct": 84,
            "recommendation_rationale": [
                "Market timing: AI in drug discovery is at inflection point (11.3% CAGR 2025-2035). First-mover advantage in platform leadership is worth ~$200M of NPV spread vs. competitors.",
                "Financial superiority: AI platform delivers 620 basis points higher NPV vs. traditional portfolio, with 13.7 percentage points higher IRR—despite higher capex and longer payback.",
                "Execution feasibility: 4-year timeline is achievable with focused team and strategic partnerships. Biologics option has 2-year longer development cycle with lower margin of safety.",
                "Risk-adjusted returns: Top 3 risks (data quality, talent, regulatory) are all addressable with proactive governance and partnerships. No black-swan technical blockers identified.",
                "Portfolio optionality: Platform success opens doors to royalty streams, licensing, and M&A upside beyond $980M base case.",
            ],
            "secondary_choice": "biologics_expansion",
            "secondary_rationale": "Pursue as complementary adjacent strategy post-launch (Y3+); validates platform on real science",
            "tertiary_choice": "traditional_portfolio",
            "tertiary_rationale": "Consider only if AI platform implementation fundamentally derails; provides lower-risk fallback but limits upside",
        },
        "evidence_scorecard": {
            "ai_platform": {
                "scientific_feasibility": 7.8,
                "financial_sustainability": 8.4,
                "market_competitiveness": 8.9,
                "healthcare_impact": 8.1,
                "composite_score": 8.3,
                "overall_rank": 1,
            },
            "biologics_expansion": {
                "scientific_feasibility": 8.2,
                "financial_sustainability": 7.2,
                "market_competitiveness": 7.4,
                "healthcare_impact": 8.6,
                "composite_score": 7.9,
                "overall_rank": 2,
            },
            "traditional_portfolio": {
                "scientific_feasibility": 8.6,
                "financial_sustainability": 6.7,
                "market_competitiveness": 6.2,
                "healthcare_impact": 6.5,
                "composite_score": 7.0,
                "overall_rank": 3,
            },
        },
        "financial_snapshot": {
            "ai_platform": {
                "capex_musd": 230,
                "npv_at_10pct_musd": 980,
                "irr_pct": 28.5,
                "payback_year": 6.8,
                "5yr_cumulative_revenue_musd": 73.5,
            },
            "biologics_expansion": {
                "capex_musd": 190,
                "npv_at_10pct_musd": 760,
                "irr_pct": 19.2,
                "payback_year": 7.5,
                "5yr_cumulative_revenue_musd": 46.0,
            },
            "traditional_portfolio": {
                "capex_musd": 160,
                "npv_at_10pct_musd": 610,
                "irr_pct": 14.8,
                "payback_year": 5.3,
                "5yr_cumulative_revenue_musd": 75.5,
            },
        },
        "market_context": {
            "tam_2026_musd": 5100,
            "tam_cagr_2025_2035_pct": 11.3,
            "novacura_sam_2026_musd": 420,  # Approx
            "novacura_som_conservative_2031_musd": 126,
            "novacura_som_optimistic_2031_musd": 294,
            "market_insight": "AI in drug discovery market is the fastest-growing pharma tech subsegment. NovaCura's platform opportunity spans $126-294M SOM by 2031 depending on product-market fit and GTM execution.",
        },
        "top_3_risks": [
            {
                "rank": 1,
                "title": "Regulatory skepticism of AI predictions without clinical validation",
                "probability_pct": 75,
                "impact_pct": 80,
                "mitigation": "Engage FDA early (2026 Q2); design validation studies now; independent advisory board; transparency reporting"
            },
            {
                "rank": 2,
                "title": "Data quality and governance bottlenecks limit model accuracy",
                "probability_pct": 65,
                "impact_pct": 85,
                "mitigation": "Data governance council; partner with pharma data consortiums; baseline bias audits; active learning framework"
            },
            {
                "rank": 3,
                "title": "AI-native competitors (Recursion, Insilico) gain market share during development",
                "probability_pct": 75,
                "impact_pct": 80,
                "mitigation": "Accelerate time-to-first-hit; strategic partnerships; differentiation on explainability + regulatory compliance"
            },
        ],
        "top_3_partnerships": [
            {
                "rank": 1,
                "partner_name": "Computational Biology CRO (e.g., Recursion, Benchling ecosystem)",
                "type": "Technology enabler",
                "rationale": "Accelerate wet-lab integration and active-learning feedback loops",
                "deal_economics": "Equity co-invest (10-15%) or royalty (2-3% on platform revenue)",
            },
            {
                "rank": 2,
                "partner_name": "Pharma Data Consortium (e.g., TransCelerate, PharmGKB)",
                "type": "Data provider",
                "rationale": "Access validated clinical outcomes for model training and validation",
                "deal_economics": "Membership fee ($500K-2M annually) + IP sharing agreement",
            },
            {
                "rank": 3,
                "partner_name": "Cloud HPC Provider (e.g., AWS, Google Cloud)",
                "type": "Infrastructure partner",
                "rationale": "Scalable compute for molecular simulations and ML model training",
                "deal_economics": "Committed spend discount (30%+) and joint GTM",
            },
        ],
        "implementation_roadmap": {
            "phase_1_foundation": {
                "duration_months": 6,
                "headline": "Build Data + Team + Governance Foundation",
                "key_outcomes": [
                    "Data governance council formed; initial audit of 500+ internal compounds",
                    "Hire Head of AI, VP Regulatory Affairs, Data Engineer lead (10 FTE total)",
                    "Establish FDA pre-submission meeting and publish AI transparency framework",
                    "Negotiate CRO + data consortium partnerships",
                ],
                "go_no_go_gates": [
                    "FDA pre-sub meeting completed with positive feedback",
                    "Data governance roadmap approved by board",
                    "Top-3 partnership LOIs signed",
                ]
            },
            "phase_2_pilots": {
                "duration_months": 12,
                "headline": "Proof-of-Concept + Clinical Integration Pilots",
                "key_outcomes": [
                    "First AI-driven hit generated in oncology target (validated in wet lab)",
                    "Active learning pipeline deployed with 50 compounds labeled",
                    "Regulatory transparency report v1 published; FDA feedback incorporated",
                    "Cloud ML infrastructure live; 500+ compounds in feature store",
                ],
                "go_no_go_gates": [
                    "First wet-lab hit meets binding affinity targets",
                    "Active learning AUC improvement > 5% vs. baseline",
                    "Regulatory feedback: no major compliance gaps identified",
                ]
            },
            "phase_3_scale": {
                "duration_months": 18,
                "headline": "Scale Platform + Commercialize",
                "key_outcomes": [
                    "3 additional therapeutic area models validated",
                    "CRO partnership fully integrated; 200+ compounds processed annually",
                    "Commercial platform launch (internal tool → licensed to partners)",
                    "Series B fundraise (if external); alternatively, partnership licensing revenue",
                ],
                "go_no_go_gates": [
                    "2 partner pharma companies signed as paying platform users",
                    "Model performance holds vs. public benchmarks (Tox21, ADMET)",
                    "Cumulative revenue > $30M; break-even on AI team capex",
                ]
            },
        },
        "key_metrics_and_kpis": {
            "scientific": [
                "Time-to-first-hit: target 18 months (vs. historical 36 months)",
                "Model AUC on hold-out test set: target 0.85+",
                "Wet-lab validation rate: target 70%+ of top 10 predictions pass binding threshold",
                "Active learning uplift: target 10%+ AUC improvement per 100 labeled compounds",
            ],
            "financial": [
                "Year 1-2 cumulative revenue: target $10M+ (pilot customers + licensing)",
                "Capex spend vs. plan: hold to ±15% variance",
                "Opex/revenue ratio by Year 5: target < 0.5x (platform leverage point)",
            ],
            "regulatory": [
                "Regulatory filing timeline: target IND within 2 years for lead oncology compound",
                "Transparency report: 90%+ stakeholder confidence in AI governance",
                "Bias audit completion: target 100% of models audited for subgroup performance variance",
            ],
            "competitive": [
                "Platform feature parity vs. Recursion/Insilico: target 80%+ on key capabilities",
                "Customer NPS: target 50+ by Year 3",
                "Market share in $126M TAM: target 10-15% by 2031 (conservative SOM scenario)",
            ],
        },
        "next_90_days": [
            {
                "priority": "critical",
                "action": "Initiate FDA pre-submission meeting for AI drug discovery pathway",
                "owner": "VP Regulatory Affairs",
                "due_date": "2026-04-15",
                "success_criteria": "Meeting scheduled; FDA feedback incorporated into compliance roadmap",
            },
            {
                "priority": "critical",
                "action": "Hire Head of AI and VP Regulatory Affairs",
                "owner": "Chief HR Officer",
                "due_date": "2026-04-30",
                "success_criteria": "2 executives on-boarded; full team plan established",
            },
            {
                "priority": "high",
                "action": "Form data governance council with board observer",
                "owner": "Chief Data Officer",
                "due_date": "2026-05-15",
                "success_criteria": "Council charter signed; first 3 meeting agenda items defined",
            },
            {
                "priority": "high",
                "action": "Sign partnership LOI with CRO for wet-lab feedback loops",
                "owner": "Chief Strategy Officer",
                "due_date": "2026-05-01",
                "success_criteria": "LOI signed; Phase 1 pilot plan documented",
            },
        ],
        "board_approval_points": [
            "Recommend AI Platform as primary strategy (84% confidence)",
            "Approve $230M capex over 4 years with gated investment (Phase gates: Y1 $65M, Y2 $57M, Y3 $42M, Y4 $20M)",
            "Authorize CFO to initiate Series B fundraising in parallel with partnership revenue (target $100M+ capital raise Y2-Y3)",
            "Empower Chief Strategy Officer to negotiate partnerships; delegate authority up to $10M annual partnership spend",
            "Establish board-level Regulatory & Risk Committee to oversee top-10 risks quarterly",
        ],
    }
