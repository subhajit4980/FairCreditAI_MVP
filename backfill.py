import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faircredit.settings')
django.setup()

from core.models import ScoreReport
from django.utils.translation import gettext as _

reports = ScoreReport.objects.all()
count = 0
for r in reports:
    ai = r.ai_assessment
    if not ai or 'Business_Explanation' not in ai:
        continue
    biz = ai['Business_Explanation']
    if 'Score_Factors' in biz:
        continue

    # Extract required values
    risk = biz.get('Risk_Decomposition', {})
    fin = biz.get('Financial_Cashflow_Analysis', {})
    
    pd_prob = risk.get('Probability_of_Default_PD', 0.2)
    fraud_prob = risk.get('Fraud_Probability', 0.05)
    income_stability = fin.get('Income_Stability_Index', 0.7)
    savings_ratio = fin.get('Savings_Ratio', 0.1)

    pd_factor = (1.0 - pd_prob) * 45
    stability_factor = min(1.0, income_stability) * 30
    fraud_factor = (1.0 - fraud_prob) * 15
    savings_factor = max(0.0, min(1.0, savings_ratio + 0.5)) * 10

    repayment_pts = int(round(pd_factor))
    repayment_deficit = 45 - repayment_pts
    stability_pts = int(round(stability_factor))
    stability_deficit = 30 - stability_pts
    fraud_pts = int(round(fraud_factor))
    fraud_deficit = 15 - fraud_pts
    savings_pts = int(round(savings_factor))
    savings_deficit = 10 - savings_pts

    helped = [
        {"label": _("Repayment capacity (low default risk)"), "pts": f"+{repayment_pts} pts"},
        {"label": _("Income stability"), "pts": f"+{stability_pts} pts"},
        {"label": _("Clean profile (low fraud risk)"), "pts": f"+{fraud_pts} pts"},
        {"label": _("Savings cushion"), "pts": f"+{savings_pts} pts"}
    ]

    hurt = []
    if repayment_deficit > 0:
        hurt.append({"label": _("Repayment capacity (low default risk) below target"), "pts": f"-{repayment_deficit} pts"})
    if stability_deficit > 0:
        hurt.append({"label": _("Income stability below target"), "pts": f"-{stability_deficit} pts"})
    if fraud_deficit > 0:
        hurt.append({"label": _("High fraud risk indicators"), "pts": f"-{fraud_deficit} pts"})
    if savings_deficit > 0:
        hurt.append({"label": _("Low savings cushion"), "pts": f"-{savings_deficit} pts"})

    biz['Score_Factors'] = {
        'helped': helped,
        'hurt': hurt
    }
    
    r.ai_assessment = ai
    r.save()
    count += 1

print(f"Updated {count} existing score reports with SHAP-style Score Factors.")
