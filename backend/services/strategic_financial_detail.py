"""
Strategic Financial Detail Engine for PharmaNeXus
Provides detailed capex/opex breakdown, cashflow waterfalls, and strategy-level financial metrics
"""

from typing import Dict, List, Any

def get_financial_detail_by_option() -> Dict[str, Any]:
    """
    Return detailed financial breakdown for all three strategic options
    Includes capex, opex, annual cashflow, sensitivity
    """
    
    # Option 1: AI Platform ($230M capex over 4 years)
    ai_option = {
        "option_id": "ai_platform",
        "option_name": "AI-Driven Drug Discovery Platform",
        "total_capex_musd": 230,
        "capex_breakdown": {
            "data_infrastructure": {
                "year_1": 25,
                "year_2": 20,
                "year_3": 15,
                "year_4": 10,
                "category_total": 70,
                "description": "Data warehouses, lakehouses, compute clusters, storage, security infrastructure"
            },
            "ai_ml_platform": {
                "year_1": 30,
                "year_2": 28,
                "year_3": 22,
                "year_4": 12,
                "category_total": 92,
                "description": "ML platform engineering, model registry, feature store, explainability tools, monitoring"
            },
            "scientific_compute": {
                "year_1": 18,
                "year_2": 16,
                "year_3": 12,
                "year_4": 8,
                "category_total": 54,
                "description": "GPU clusters, simulation tools, docking engines, cheminformatics software"
            },
            "crm_partnerships": {
                "year_1": 12,
                "year_2": 10,
                "year_3": 8,
                "year_4": 4,
                "category_total": 34,
                "description": "CRO integrations, lab automation partnerships, tech vendor agreements"
            },
        },
        "opex_by_function": {
            "r_d_ai_team": {
                "headcount_year1": 15,
                "headcount_year5": 35,
                "salary_burden_per_person_musd": 0.25,
                "year_1_opex": 3.75,
                "year_2_opex": 6.0,
                "year_3_opex": 8.25,
                "year_4_opex": 10.5,
                "year_5_opex": 8.75,
                "description": "PhD ML engineers, computational chemists, data scientists, ML ops"
            },
            "regulatory_compliance": {
                "headcount_year1": 3,
                "headcount_year5": 8,
                "salary_burden_per_person_musd": 0.20,
                "year_1_opex": 0.6,
                "year_2_opex": 1.2,
                "year_3_opex": 1.8,
                "year_4_opex": 2.4,
                "year_5_opex": 1.6,
                "description": "GxP/21 CFR, transparency reporting, regulatory affairs"
            },
            "commercial_operations": {
                "headcount_year1": 4,
                "headcount_year5": 12,
                "salary_burden_per_person_musd": 0.18,
                "year_1_opex": 0.72,
                "year_2_opex": 1.2,
                "year_3_opex": 1.8,
                "year_4_opex": 2.4,
                "year_5_opex": 2.16,
                "description": "Sales, partnerships, business development"
            },
            "facilities_it": {
                "year_1_opex": 1.2,
                "year_2_opex": 1.5,
                "year_3_opex": 1.8,
                "year_4_opex": 2.1,
                "year_5_opex": 2.4,
                "description": "Office space, compute hosting, cloud services, security"
            },
        },
        "annual_cashflow": {
            "year_1": {
                "capex": -65,
                "opex": -6.27,
                "revenue": 0,
                "net_cashflow": -71.27,
            },
            "year_2": {
                "capex": -57,
                "opex": -9.9,
                "revenue": 2.5,
                "net_cashflow": -64.4,
            },
            "year_3": {
                "capex": -42,
                "opex": -13.65,
                "revenue": 8.0,
                "net_cashflow": -47.65,
            },
            "year_4": {
                "capex": -26,
                "opex": -17.4,
                "revenue": 18.0,
                "net_cashflow": -25.4,
            },
            "year_5": {
                "capex": -40,  # Expansion capex
                "opex": -15.16,
                "revenue": 45.0,
                "net_cashflow": -10.16,
            },
        },
        "financial_outcomes_5yr": {
            "cumulative_capex_musd": 230,
            "cumulative_opex_musd": 62.38,
            "cumulative_revenue_musd": 73.5,
            "net_cumulative_cashflow_musd": -218.88,
            "npv_at_10pct_discount_musd": 980,
            "irr_pct": 28.5,
            "payback_year": 6.8,
        },
        "sensitivity_tornado": {
            "base_npv_musd": 980,
            "variables": {
                "ai_accuracy": {
                    "impact_range_musd": [750, 1120],
                    "sensitivity_pct_per_10pct": 18,
                },
                "revenue_ramp": {
                    "impact_range_musd": [620, 1340],
                    "sensitivity_pct_per_10pct": 36,
                },
                "capex_overrun": {
                    "impact_range_musd": [870, 1090],
                    "sensitivity_pct_per_10pct": 11,
                },
                "opex_per_headcount": {
                    "impact_range_musd": [920, 1040],
                    "sensitivity_pct_per_10pct": 6,
                },
                "discount_rate": {
                    "impact_range_musd": [750, 1150],
                    "sensitivity_pct_per_10pct": 17,
                },
            },
            "top_driver": "Revenue ramp (customer adoption + contract value growth)",
        }
    }
    
    # Option 2: Biologics ($190M capex)
    biologics_option = {
        "option_id": "biologics_expansion",
        "option_name": "Biologics and Precision Therapeutics Expansion",
        "total_capex_musd": 190,
        "capex_breakdown": {
            "manufacturing_facility": {
                "year_1": 45,
                "year_2": 40,
                "year_3": 20,
                "year_4": 15,
                "category_total": 120,
                "description": "GMP manufacturing, fill-finish, cold-chain facilities"
            },
            "r_d_infrastructure": {
                "year_1": 15,
                "year_2": 12,
                "year_3": 10,
                "year_4": 8,
                "category_total": 45,
                "description": "Antibody engineering labs, cell line development, assay platforms"
            },
            "regulatory_cmmc": {
                "year_1": 8,
                "year_2": 8,
                "year_3": 5,
                "year_4": 4,
                "category_total": 25,
                "description": "CMC studies, regulatory dossiers, stability testing"
            },
        },
        "opex_by_function": {
            "manufacturing_operations": {
                "headcount_year1": 25,
                "headcount_year5": 50,
                "salary_burden_per_person_musd": 0.15,
                "year_1_opex": 3.75,
                "year_2_opex": 5.1,
                "year_3_opex": 6.45,
                "year_4_opex": 7.8,
                "year_5_opex": 7.5,
                "description": "Manufacturing technicians, QA/QC, supply chain"
            },
            "clinical_development": {
                "headcount_year1": 12,
                "headcount_year5": 30,
                "salary_burden_per_person_musd": 0.22,
                "year_1_opex": 2.64,
                "year_2_opex": 4.4,
                "year_3_opex": 6.16,
                "year_4_opex": 7.92,
                "year_5_opex": 6.6,
                "description": "Clinical operations, medical affairs, CRO management"
            },
            "regulatory_affairs": {
                "headcount_year1": 4,
                "headcount_year5": 10,
                "salary_burden_per_person_musd": 0.20,
                "year_1_opex": 0.8,
                "year_2_opex": 1.4,
                "year_3_opex": 2.0,
                "year_4_opex": 2.6,
                "year_5_opex": 2.0,
                "description": "IND/BLA submissions, regulatory strategy"
            },
        },
        "annual_cashflow": {
            "year_1": {"capex": -50, "opex": -7.19, "revenue": 0, "net_cashflow": -57.19},
            "year_2": {"capex": -48, "opex": -10.9, "revenue": 1.0, "net_cashflow": -57.9},
            "year_3": {"capex": -33, "opex": -14.61, "revenue": 5.0, "net_cashflow": -42.61},
            "year_4": {"capex": -27, "opex": -18.32, "revenue": 12.0, "net_cashflow": -33.32},
            "year_5": {"capex": -32, "opex": -16.1, "revenue": 28.0, "net_cashflow": -20.1},
        },
        "financial_outcomes_5yr": {
            "cumulative_capex_musd": 190,
            "cumulative_opex_musd": 67.12,
            "cumulative_revenue_musd": 46.0,
            "net_cumulative_cashflow_musd": -211.12,
            "npv_at_10pct_discount_musd": 760,
            "irr_pct": 19.2,
            "payback_year": 7.5,
        },
    }
    
    # Option 3: Traditional ($160M capex)
    traditional_option = {
        "option_id": "traditional_portfolio",
        "option_name": "Traditional Small-Molecule Portfolio Optimization",
        "total_capex_musd": 160,
        "capex_breakdown": {
            "chemistry_labs": {
                "year_1": 30,
                "year_2": 25,
                "year_3": 15,
                "year_4": 10,
                "category_total": 80,
                "description": "Chemistry labs, analytical instruments, compound libraries"
            },
            "scale_up": {
                "year_1": 20,
                "year_2": 18,
                "year_3": 15,
                "year_4": 12,
                "category_total": 65,
                "description": "Pilot plant, manufacturing process optimization"
            },
            "formulation_packaging": {
                "year_1": 8,
                "year_2": 7,
                "year_3": 0,
                "year_4": 0,
                "category_total": 15,
                "description": "Formulation development, packaging equipment"
            },
        },
        "opex_by_function": {
            "medicinal_chemistry": {
                "headcount_year1": 18,
                "headcount_year5": 28,
                "salary_burden_per_person_musd": 0.20,
                "year_1_opex": 3.6,
                "year_2_opex": 4.8,
                "year_3_opex": 5.6,
                "year_4_opex": 6.4,
                "year_5_opex": 5.6,
                "description": "Medicinal chemists, analytical chemists, lab technicians"
            },
            "drug_safety": {
                "headcount_year1": 6,
                "headcount_year5": 12,
                "salary_burden_per_person_musd": 0.18,
                "year_1_opex": 1.08,
                "year_2_opex": 1.6,
                "year_3_opex": 2.16,
                "year_4_opex": 2.72,
                "year_5_opex": 2.16,
                "description": "DMPK studies, toxicology support"
            },
        },
        "annual_cashflow": {
            "year_1": {"capex": -48, "opex": -4.68, "revenue": 1.5, "net_cashflow": -51.18},
            "year_2": {"capex": -42, "opex": -6.4, "revenue": 5.0, "net_cashflow": -43.4},
            "year_3": {"capex": -30, "opex": -7.76, "revenue": 12.0, "net_cashflow": -25.76},
            "year_4": {"capex": -22, "opex": -9.12, "revenue": 22.0, "net_cashflow": -9.12},
            "year_5": {"capex": -18, "opex": -7.76, "revenue": 35.0, "net_cashflow": 9.24},
        },
        "financial_outcomes_5yr": {
            "cumulative_capex_musd": 160,
            "cumulative_opex_musd": 35.72,
            "cumulative_revenue_musd": 75.5,
            "net_cumulative_cashflow_musd": -120.22,
            "npv_at_10pct_discount_musd": 610,
            "irr_pct": 14.8,
            "payback_year": 5.3,
        },
    }
    
    return {
        "by_option": {
            "ai_platform": ai_option,
            "biologics_expansion": biologics_option,
            "traditional_portfolio": traditional_option,
        },
        "comparison_summary": {
            "ai_platform": {
                "total_capex_musd": 230,
                "cumulative_opex_5yr_musd": 62.38,
                "npv_musd": 980,
                "irr_pct": 28.5,
                "payback_year": 6.8,
            },
            "biologics_expansion": {
                "total_capex_musd": 190,
                "cumulative_opex_5yr_musd": 67.12,
                "npv_musd": 760,
                "irr_pct": 19.2,
                "payback_year": 7.5,
            },
            "traditional_portfolio": {
                "total_capex_musd": 160,
                "cumulative_opex_5yr_musd": 35.72,
                "npv_musd": 610,
                "irr_pct": 14.8,
                "payback_year": 5.3,
            },
        }
    }
