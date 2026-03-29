from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib.units import cm
from io import BytesIO
from datetime import datetime

BRAND_GREEN  = colors.HexColor("#0F6E56")
BRAND_LIGHT  = colors.HexColor("#E1F5EE")
BRAND_DARK   = colors.HexColor("#085041")
GRAY_LIGHT   = colors.HexColor("#F1EFE8")
GRAY_TEXT    = colors.HexColor("#5F5E5A")
DANGER_RED   = colors.HexColor("#A32D2D")
WARN_AMBER   = colors.HexColor("#854F0B")

def generate_executive_report(report_data: dict) -> bytes:
    """
    report_data: {
        "company": str,
        "date": str,
        "prepared_by": str,
        "recommendation": str,
        "confidence_score": float,       # 0-1
        "strategy": str,
        "key_metrics": [{"label":str, "value":str, "note":str}],
        "risk_register": [{"title":str, "level":"high"|"med"|"low", "desc":str}],
        "compounds": [{"name":str, "probability":float, "recommendation":str}],
        "model_info": {"type":str, "accuracy":float, "training_samples":int}
    }
    Returns: bytes (PDF)
    """
    buf    = BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               topMargin=2*cm, bottomMargin=2*cm,
                               leftMargin=2.5*cm, rightMargin=2.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    # ---- Cover ----
    cover_style = ParagraphStyle("cover", fontSize=28, textColor=BRAND_DARK,
                                  spaceAfter=8, fontName="Helvetica-Bold")
    sub_style   = ParagraphStyle("sub", fontSize=13, textColor=GRAY_TEXT,
                                  spaceAfter=4, fontName="Helvetica")
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph(report_data.get("company","NovaCura Therapeutics"), cover_style))
    story.append(Paragraph("Strategic Investment Intelligence Report", sub_style))
    story.append(Paragraph(f"Prepared: {report_data.get('date', datetime.today().strftime('%B %d, %Y'))}", sub_style))
    story.append(Paragraph(f"Prepared by: {report_data.get('prepared_by','Strategy Team')}", sub_style))
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN))
    story.append(Spacer(1, 0.5*cm))

    # Recommendation box
    rec = report_data.get("recommendation","AI-Driven Drug Discovery Platform")
    conf = report_data.get("confidence_score", 0.87)
    rec_table = Table(
        [[Paragraph(f"<b>Recommendation</b>", styles["Normal"]),
          Paragraph(f"<b>{rec}</b>", styles["Normal"])],
         [Paragraph("Confidence Score", styles["Normal"]),
          Paragraph(f"{conf*100:.0f}%", styles["Normal"])]],
        colWidths=[5*cm, 11*cm]
    )
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_GREEN),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), BRAND_LIGHT),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 11),
        ("PADDING",    (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [BRAND_GREEN, BRAND_LIGHT]),
    ]))
    story.append(rec_table)
    story.append(PageBreak())

    # ---- Key Metrics ----
    h2 = ParagraphStyle("h2", fontSize=16, textColor=BRAND_DARK,
                          fontName="Helvetica-Bold", spaceAfter=10)
    story.append(Paragraph("Key Performance Metrics", h2))
    metrics = report_data.get("key_metrics", [
        {"label":"Total Budget",         "value":"$500M",   "note":"5-year horizon"},
        {"label":"Expected NPV (AI)",    "value":"$1.24B",  "note":"@ 10% discount rate"},
        {"label":"IRR",                  "value":"31.4%",   "note":"Internal rate of return"},
        {"label":"Break-even Year",      "value":"3.2",     "note":"Platform licensing"},
        {"label":"AI Probability Uplift","value":"2.8x",    "note":"vs 8.2% industry baseline"},
        {"label":"Phase 1 PoS",          "value":"68.4%",   "note":"AI-enhanced"},
    ])
    metric_rows = [["Metric","Value","Note"]] + [
        [m["label"], m["value"], m.get("note","")] for m in metrics
    ]
    mt = Table(metric_rows, colWidths=[7*cm, 4*cm, 5.5*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), BRAND_DARK),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("PADDING",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, GRAY_LIGHT]),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
    ]))
    story.append(mt)
    story.append(Spacer(1, 0.8*cm))

    # ---- Compound Pipeline ----
    story.append(Paragraph("Compound Pipeline — Model Predictions", h2))
    compounds = report_data.get("compounds", [
        {"name":"Compound A","probability":0.78,"recommendation":"Proceed to Phase 1"},
        {"name":"Compound B","probability":0.42,"recommendation":"Caution — optimise binding"},
        {"name":"Compound C","probability":0.91,"recommendation":"Priority candidate"},
    ])
    comp_rows = [["Compound","Success Probability","Model Recommendation"]] + [
        [c["name"], f"{c['probability']*100:.1f}%", c["recommendation"]]
        for c in compounds
    ]
    ct = Table(comp_rows, colWidths=[5*cm, 5*cm, 6.5*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_GREEN),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 10),
        ("PADDING",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, BRAND_LIGHT]),
        ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # ---- Risk Register ----
    story.append(Paragraph("Risk Register", h2))
    risks = report_data.get("risk_register", [
        {"title":"Regulatory AI Acceptance","level":"high","desc":"FDA frameworks still evolving"},
        {"title":"Data Quality & Scarcity","level":"high","desc":"2-4 years to build data moat"},
        {"title":"Talent Acquisition","level":"med","desc":"18-month hiring runway needed"},
        {"title":"IP Uncertainty","level":"med","desc":"AI-generated compound IP contested"},
        {"title":"Clinical Execution","level":"low","desc":"AI trial design reduces variance"},
    ])
    level_colors = {"high": DANGER_RED, "med": WARN_AMBER, "low": BRAND_GREEN}
    risk_rows = [["Risk","Level","Description"]] + [
        [r["title"], r["level"].upper(), r["desc"]] for r in risks
    ]
    rt = Table(risk_rows, colWidths=[5.5*cm, 2.5*cm, 8.5*cm])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BRAND_DARK),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("PADDING",    (0,0), (-1,-1), 7),
        ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
        *[("TEXTCOLOR", (1, i+1), (1, i+1),
           level_colors.get(risks[i]["level"], GRAY_TEXT))
          for i in range(len(risks))],
        *[("FONTNAME", (1, i+1), (1, i+1), "Helvetica-Bold")
          for i in range(len(risks))],
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.8*cm))

    # ---- Model Methodology Appendix ----
    story.append(Paragraph("Appendix — Model Methodology", h2))
    model_info = report_data.get("model_info", {
        "type": "Random Forest Classifier (sklearn)",
        "accuracy": 0.84,
        "training_samples": 300
    })
    body_style = ParagraphStyle("body", fontSize=10, textColor=GRAY_TEXT,
                                 leading=16, fontName="Helvetica")
    story.append(Paragraph(
        f"Model type: {model_info.get('type','Random Forest')}. "
        f"Training samples: {model_info.get('training_samples',300)}. "
        f"Cross-validated accuracy: {model_info.get('accuracy',0.84)*100:.1f}%. "
        "Input features: toxicity, bioavailability, solubility, binding affinity, "
        "and normalised molecular weight (all scaled 0-1). "
        "Success threshold defined as overall probability of approval > 50%. "
        "SHAP TreeExplainer used for feature attribution. "
        "Confidence bands derived from per-tree variance in the Random Forest ensemble.",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#D3D1C7")))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Confidential — {report_data.get('company','NovaCura Therapeutics')} — "
        f"Generated {datetime.today().strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle("footer", fontSize=8, textColor=GRAY_TEXT,
                        fontName="Helvetica", alignment=1)
    ))

    doc.build(story)
    return buf.getvalue()
