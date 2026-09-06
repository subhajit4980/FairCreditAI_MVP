import re

file_path = "templates/core/score_detail.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add {% load i18n %} if not there
if "{% load i18n %}" not in content:
    content = content.replace("{% extends \"core/base.html\" %}", "{% extends \"core/base.html\" %}\n{% load i18n %}")

# Regex to find HTML elements with text
patterns = [
    r'(<h[1-6][^>]*>)\s*([^<{%]+?)\s*(</h[1-6]>)',
    r'(<label[^>]*>)\s*([^<{%]+?)\s*(</label>)',
    r'(<th[^>]*>)\s*([^<{%]+?)\s*(</th>)',
    r'(<div class="lbl"[^>]*>)\s*([^<{%]+?)\s*(</div>)',
    r'(<div class="status-title"[^>]*>)\s*([^<{%]+?)\s*(</div>)',
    r'(<div class="portal-badge[^>]*>)\s*([^<{%]+?)\s*(</div>)',
    r'(<span class="risk-title"[^>]*>)\s*([^<{%]+?)\s*(</span>)',
    r'(<div class="band-label"[^>]*>)\s*([^<{%]+?)\s*(</div>)',
]

for pat in patterns:
    def repl(m):
        prefix, text, suffix = m.groups()
        text = text.strip()
        # if text is already translated or contains django tags, skip
        if not text or '{%' in text or '{{' in text or 'trans ' in text:
            return m.group(0)
        # Avoid numbers only or symbols
        if re.match(r'^[\d\W]+$', text):
            return m.group(0)
        
        return f'{prefix}{{% trans "{text}" %}}{suffix}'
    
    content = re.sub(pat, repl, content)

# Manual replacements for specific known strings
replacements = {
    'Download Transactions (Excel)': '{% trans "Download Transactions (Excel)" %}',
    'Back to customer details': '{% trans "Back to customer details" %}',
    'Back to dashboard': '{% trans "Back to dashboard" %}',
    'Score Unavailable': '{% trans "Score Unavailable" %}',
    'Calculated Monthly Income (Verified Statement/Profile)': '{% trans "Calculated Monthly Income (Verified Statement/Profile)" %}',
    'Calculated Monthly Expense': '{% trans "Calculated Monthly Expense" %}',
    'FOIR % (Debt Obligations / Monthly Income)': '{% trans "FOIR % (Debt Obligations / Monthly Income)" %}',
    'Available Surplus Disposable Income': '{% trans "Available Surplus Disposable Income" %}',
    'Income Stability Score': '{% trans "Income Stability Score" %}',
    'Savings Ratio': '{% trans "Savings Ratio" %}',
    'Essential vs. Discretionary Expense Split': '{% trans "Essential vs. Discretionary Expense Split" %}',
    'Operations console for partner banks': '{% trans "Operations console for partner banks" %}',
}
for k, v in replacements.items():
    if k not in content or '{% trans "'+k+'" %}' in content:
        continue
    content = content.replace(f">{k}<", f">{v}<")
    content = content.replace(f" {k} ", f" {v} ")
    # for Back to...
    content = content.replace(f"&larr; {k}", f"&larr; {v}")


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated score_detail.html successfully!")
