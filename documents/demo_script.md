# FairCreditScore: 2.5-Minute Pitch & Live Demo Script

This script is professionally engineered to fit exactly within a **2.5-minute (150-second) constraint** (standard speaking pace of ~140 words per minute). It covers the full customer flow, backoffice verification, and lender API integration.

---

## 🛠️ Demo Credentials Cheat Sheet
Keep this table open on a secondary screen or notepad for quick copying:

| Role | Username | Password | Actions / Key Highlights |
| :--- | :--- | :--- | :--- |
| **Customer** | `ramesh` | `demo12345` | Dashboard, Uploaded IDs, AA Consent, Score Dial, Underwriting Grade |
| **Operations** | `ops` | `ops12345` | Document Queue, Customer Search, Verify & Approve PAN Card |
| **Administrator** | `admin` | `admin12345` | KPI Dashboard, Append-Only Audit Logs, Built-in Wiki |
| **Lender API** | *Any Browser Tab* | *No Auth (Demo)* | Endpoint: `/api/lender/score/1/` (Returns JSON decision) |

---

## ⏱️ Timeline & Step-by-Step Presentation Script

```
Total Word Count: ~350 words | Target Delivery Time: 2 minutes 30 seconds
```

| Time | On-Screen Visual & Actions | Spoken Script (Word-for-Word Narrative) | Presenter Tips |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:30** *(30s)* | 1. Start on the **Login Page**.<br>2. Type username `ramesh` and password `demo12345` and log in.<br>3. Point to the **Customer Dashboard** layout, showing Ramesh's profile. | "Hi everyone. Over seventy million digital-first merchants and gig-workers in India are credit-starved because traditional credit bureaus require formal history. Meet **FairCreditScore**. We bypass traditional bureau scores by analyzing alternative cashflow data under user consent.<br><br>Logging in as Ramesh, our Kirana shop owner, we see his personal dashboard. Ramesh has uploaded his PAN card and Aadhaar for verification, which are currently awaiting operational review." | Start speaking immediately after logging in. Speak clearly and maintain a steady pace. |
| **0:30 - 1:00** *(30s)* | 1. Click **"Initiate Consent"** (Account Aggregator).<br>2. Enters mock handle (e.g., `ramesh@setu`).<br>3. On the mock Setu screen, click **Approve** and type OTP `123456`. Click submit.<br>4. Redirects back to Dashboard showing **Active Consent**. | "To evaluate cashflow, Ramesh grants secure access to his transaction history. With a single click, we trigger the Account Aggregator consent flow. This redirects him to our simulated Setu Bridge consent portal.<br><br>Here, Ramesh reviews what data is shared, enters the secure verification OTP `123456`, and approves. Instantaneously, his consent status is updated to active, unlocking his banking footprint." | Execute the OTP entry quickly; do not wait or hesitate. |
| **1:00 - 1:40** *(40s)* | 1. Click the **"Get the Score and Loan Eligibility"** button.<br>2. Reveal the **Alternative Credit Score Dial** gauge (e.g., Score 59, Grade C).<br>3. Point to the seven features and explainable AI factors (positive/negative). | "Now, the underwriting engine runs. By generating Ramesh's credit score, our engine processes alternative cashflow data under user consent, analyzing parameters like income recurrence, savings ratio, and payment timeliness.<br><br>Ramesh scores a **59 out of 100**, placing him in Grade C. Our explainable credit model highlights his key factors: positive monthly savings and a clean repayment history with zero bounces, offset by an income recurrence rate below target. Ramesh is pre-approved for a loan of 1.3 lakhs at 14.5% interest." | Use mouse cursor to hover over the score dial and the top positive/negative factors. |
| **1:40 - 2:15** *(35s)* | 1. Log out of Ramesh's account.<br>2. Log in as `ops` with password `ops12345`.<br>3. Navigate to **Pending Documents**; click Ramesh's PAN card.<br>4. Enter note: *"PAN is clear and verified."* Click **Approve**.<br>5. Open a new tab to `/api/lender/score/1/` to show JSON data. | "Let's pivot to the backoffice. Logging in as the Operations reviewer, we view our verification queue. We inspect Ramesh's PAN upload, confirm its validity, add a quick review note, and approve it.<br><br>Finally, for our lending partners, we expose a clean, secure REST API. A simple GET request returns Ramesh’s underwriting verdict, interest band, and recommended loan limit in structured JSON, ready for instant integration." | If time runs short, you can keep the API endpoint open in another tab to switch to it instantly. |
| **2:15 - 2:30** *(15s)* | 1. Switch back to the admin portal or main landing page.<br>2. Briefly show the **Wiki** page or **Audit Log** tab. | "Built on Django and Postgres, with an append-only audit trail for compliance, FairCreditScore provides a compliant, explainable, and production-ready alternative underwriting pipeline.<br><br>Thank you!" | Conclude with confidence and invite questions. |

---

## 💡 Pro-Tips for a Flawless Presentation

1. **Pre-load Tabs**: Have one tab open at the landing/login page, and another tab already logged in as `ops` or displaying the API JSON output. This prevents waiting for page reloads or typing mistakes during the 2.5-minute timer.
2. **Set the Database**: Make sure you have run `python manage.py seed_demo` before the presentation so all demo data matches the script exactly.
3. **Pacing**: Speak at a measured, professional pace. If a page load takes 1-2 seconds, use that time to gesture towards the screen.
