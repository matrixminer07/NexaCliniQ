"""
Risk Register Engine for PharmaNeXus Strategic Analysis
Aggregates and scores risks across all three investment options and roadmap
"""

from typing import Dict, List, Any

def get_unified_risk_register() -> Dict[str, Any]:
    """
    Return comprehensive risk register with probability, impact, mitigation, owner, status
    Aggregates risks from all three strategic options + roadmap phases
    """
    
    # Core risks by strategic option
    ai_platform_risks = [
        {
            "id": "risk_001",
            "category": "Data & AI",
            "title": "Poor data quality and governance bottlenecks",
            "description": "Internal data fragmented; regulatory data access limited; biases difficult to audit",
            "affected_options": ["ai_platform"],
            "probability_pct": 65,
            "impact_pct": 85,  # Impact on NPV if materialized
            "risk_score": 55,  # (prob * impact) / 100
            "mitigation_strategy": "Establish data governance council; partner with pharma data consortiums; baseline bias audits",
            "responsible_owner": "Chief Data Officer",
            "due_date": "2026-Q3",
            "status": "not_started",
            "priority": "critical",
        },
        {
            "id": "risk_002",
            "category": "Talent & Execution",
            "title": "Difficulty recruiting and retaining ML/cheminformatics specialists",
            "description": "Competitive talent market; low salaries vs. Big Tech; long onboarding for pharma domain",
            "affected_options": ["ai_platform"],
            "probability_pct": 60,
            "impact_pct": 70,
            "risk_score": 42,
            "mitigation_strategy": "Establish competitive equity packages; partner with top ML universities; in-house training program",
            "responsible_owner": "Chief HR Officer",
            "due_date": "2026-Q2",
            "status": "not_started",
            "priority": "critical",
        },
        {
            "id": "risk_003",
            "category": "Regulatory & Compliance",
            "title": "FDA / EMA skepticism of AI-derived predictions without clinical validation",
            "description": "Regulators expect real wet-lab validation; synthetic training unacceptable; slow IND approval path",
            "affected_options": ["ai_platform"],
            "probability_pct": 75,
            "impact_pct": 80,
            "risk_score": 60,
            "mitigation_strategy": "Early engagement with FDA; design validation studies now; establish regulatory advisory board",
            "responsible_owner": "VP Regulatory Affairs",
            "due_date": "2026-Q2",
            "status": "not_started",
            "priority": "critical",
        },
        {
            "id": "risk_004",
            "category": "Technical",
            "title": "Model transferability from in-silico to wet-lab",
            "description": "Lab conditions differ; compound synthesis feasibility not predicted well; attrition surprises",
            "affected_options": ["ai_platform"],
            "probability_pct": 55,
            "impact_pct": 60,
            "risk_score": 33,
            "mitigation_strategy": "Tight wet-lab feedback loops; active learning pilot; synthetic biology partnerships",
            "responsible_owner": "Head of Discovery Biology",
            "due_date": "2026-Q4",
            "status": "not_started",
            "priority": "high",
        },
    ]
    
    biologics_risks = [
        {
            "id": "risk_005",
            "category": "Execution",
            "title": "Manufacturing scale-up complexity and timeline slip",
            "description": "GMP facility buildout, antibody engineering, cell line optimization delays",
            "affected_options": ["biologics_expansion"],
            "probability_pct": 65,
            "impact_pct": 75,
            "risk_score": 49,
            "mitigation_strategy": "CDMO partnerships; platform technology licensing; staged scale-up gates",
            "responsible_owner": "VP Manufacturing",
            "due_date": "2026-Q3",
            "status": "not_started",
            "priority": "critical",
        },
        {
            "id": "risk_006",
            "category": "Market",
            "title": "Cold-chain logistics and pricing pressure in emerging markets",
            "description": "High cost-of-goods; limited reimbursement in LMIC; distribution complexity",
            "affected_options": ["biologics_expansion"],
            "probability_pct": 50,
            "impact_pct": 60,
            "risk_score": 30,
            "mitigation_strategy": "Establish logistics partnerships; pursue RAP/tiered pricing; GAVI alignment",
            "responsible_owner": "Chief Commercial Officer",
            "due_date": "2026-Q4",
            "status": "not_started",
            "priority": "high",
        },
    ]
    
    traditional_risks = [
        {
            "id": "risk_007",
            "category": "Market",
            "title": "Generic erosion and low differentiation in crowded classes",
            "description": "Small-molecule compounds face me-too competition; patent cliffs accelerate",
            "affected_options": ["traditional_portfolio"],
            "probability_pct": 70,
            "impact_pct": 70,
            "risk_score": 49,
            "mitigation_strategy": "Focus on unmet medical needs; pursue combination therapies; lifecycle management",
            "responsible_owner": "VP Portfolio Strategy",
            "due_date": "2026-Q2",
            "status": "not_started",
            "priority": "high",
        },
        {
            "id": "risk_008",
            "category": "Competitive",
            "title": "AI-native competitors gaining market share during development timeline",
            "description": "Recursion, Insilico, Schrodinger accelerating discoveries; NovaCura cycles lag",
            "affected_options": ["traditional_portfolio"],
            "probability_pct": 75,
            "impact_pct": 80,
            "risk_score": 60,
            "mitigation_strategy": "Accelerate pipeline; partner with AI vendors; strategic M&A",
            "responsible_owner": "Chief Strategy Officer",
            "due_date": "2026-Q2",
            "status": "not_started",
            "priority": "critical",
        },
    ]
    
    # Cross-cutting risks affecting all options
    crosscutting_risks = [
        {
            "id": "risk_009",
            "category": "Regulatory & Ethical",
            "title": "Regulatory focus on AI bias, transparency, and accountability escalates",
            "description": "FDA AI/ML guidance tightens; EMA AI Act enforcement begins; reputational risk from failures",
            "affected_options": ["ai_platform", "biologics_expansion", "traditional_portfolio"],
            "probability_pct": 80,
            "impact_pct": 65,
            "risk_score": 52,
            "mitigation_strategy": "Proactive compliance team; transparency reports; independent audits; stakeholder engagement",
            "responsible_owner": "Chief Compliance Officer",
            "due_date": "2026-Q2",
            "status": "not_started",
            "priority": "critical",
        },
        {
            "id": "risk_010",
            "category": "Financial",
            "title": "Capital markets downturn reduces funding for biotech R&D",
            "description": "Series B/C fundraising dries up; M&A valuations collapse; strategic pivot required",
            "affected_options": ["ai_platform", "biologics_expansion", "traditional_portfolio"],
            "probability_pct": 40,
            "impact_pct": 85,
            "risk_score": 34,
            "mitigation_strategy": "Diversify funding sources; establish strategic partnerships early; phase capital spend",
            "responsible_owner": "Chief Financial Officer",
            "due_date": "2026-Q1",
            "status": "not_started",
            "priority": "high",
        },
    ]
    
    all_risks = ai_platform_risks + biologics_risks + traditional_risks + crosscutting_risks
    
    # Compute heatmap by risk score
    critical_risks = [r for r in all_risks if r["risk_score"] >= 50]
    high_risks = [r for r in all_risks if 30 <= r["risk_score"] < 50]
    medium_risks = [r for r in all_risks if r["risk_score"] < 30]
    
    return {
        "risk_count": len(all_risks),
        "critical_count": len(critical_risks),
        "high_count": len(high_risks),
        "medium_count": len(medium_risks),
        "risks": all_risks,
        "risk_heatmap": {
            "critical": critical_risks,
            "high": high_risks,
            "medium": medium_risks,
        },
        "risk_categories": {
            "Data & AI": len([r for r in all_risks if r["category"] == "Data & AI"]),
            "Talent & Execution": len([r for r in all_risks if r["category"] == "Talent & Execution"]),
            "Regulatory & Compliance": len([r for r in all_risks if r["category"] == "Regulatory & Compliance"]),
            "Technical": len([r for r in all_risks if r["category"] == "Technical"]),
            "Execution": len([r for r in all_risks if r["category"] == "Execution"]),
            "Market": len([r for r in all_risks if r["category"] == "Market"]),
            "Competitive": len([r for r in all_risks if r["category"] == "Competitive"]),
            "Regulatory & Ethical": len([r for r in all_risks if r["category"] == "Regulatory & Ethical"]),
            "Financial": len([r for r in all_risks if r["category"] == "Financial"]),
        },
        "by_option": {
            "ai_platform": [r for r in all_risks if "ai_platform" in r["affected_options"]],
            "biologics_expansion": [r for r in all_risks if "biologics_expansion" in r["affected_options"]],
            "traditional_portfolio": [r for r in all_risks if "traditional_portfolio" in r["affected_options"]],
        },
        "top_risks_by_score": sorted(all_risks, key=lambda r: r["risk_score"], reverse=True)[:5],
        "ownership_summary": {
            owner: len([r for r in all_risks if r["responsible_owner"] == owner])
            for owner in set(r["responsible_owner"] for r in all_risks)
        },
        "status_summary": {
            "not_started": len([r for r in all_risks if r["status"] == "not_started"]),
            "in_progress": len([r for r in all_risks if r["status"] == "in_progress"]),
            "completed": len([r for r in all_risks if r["status"] == "completed"]),
        },
    }
