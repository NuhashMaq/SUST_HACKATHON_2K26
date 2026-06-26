# QueueStorm Investigator API

This is our preliminary round submission for **SUST CSE Carnival 2026 - Codex Community Hackathon**.

The project is a small FastAPI service that analyzes customer support tickets for a digital finance platform. It reads the complaint and the given transaction history, then returns a structured JSON response for support agents.

Live URL:

```txt
https://sust-hackathon-2-k26-8238.vercel.app
```

GitHub Repository:

```txt
https://github.com/NuhashMaq/SUST_HACKATHON_2K26
```

---

## Endpoints

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Analyze Ticket

```http
POST /analyze-ticket
```

This endpoint accepts one support ticket and returns the case analysis.

---

## Example Request

```json
{
  "ticket_id": "TKT-TEST-001",
  "complaint": "Someone called me and asked for my OTP saying my account will be blocked.",
  "language": "en",
  "channel": "call_center",
  "user_type": "customer",
  "transaction_history": []
}
```

## Example Response

```json
{
  "ticket_id": "TKT-TEST-001",
  "relevant_transaction_id": null,
  "evidence_verdict": "insufficient_data",
  "case_type": "phishing_or_social_engineering",
  "severity": "critical",
  "department": "fraud_risk",
  "agent_summary": "Customer reports a possible phishing or social engineering attempt involving credentials or account access.",
  "recommended_next_action": "Escalate to fraud_risk immediately. Confirm that official support never asks for PIN, OTP, or password.",
  "customer_reply": "Thank you for reaching out before sharing any information. We never ask for your PIN, OTP, or password under any circumstances. Please do not share these with anyone, even if they claim to be from us. Our fraud team has been notified.",
  "human_review_required": true,
  "confidence": 0.95,
  "reason_codes": [
    "phishing",
    "credential_protection",
    "critical_escalation"
  ]
}
```

---

## What the API Does

The API identifies:

* relevant transaction ID
* evidence verdict
* case type
* severity
* responsible department
* human review requirement
* agent summary
* recommended next step
* safe customer reply

The important part is that it does not only classify the complaint. It also checks the transaction history before making a decision.

---

## Supported Case Types

```txt
wrong_transfer
payment_failed
refund_request
duplicate_payment
merchant_settlement_delay
agent_cash_in_issue
phishing_or_social_engineering
other
```

---

## Evidence Verdicts

```txt
consistent
inconsistent
insufficient_data
```

`consistent` means the transaction history supports the complaint.

`inconsistent` means the transaction history does not fully support the complaint.

`insufficient_data` means the given data is not enough to decide safely.

---

## Department Routing

| Case Type                      | Department          |
| ------------------------------ | ------------------- |
| wrong_transfer                 | dispute_resolution  |
| payment_failed                 | payments_ops        |
| refund_request                 | customer_support    |
| duplicate_payment              | payments_ops        |
| merchant_settlement_delay      | merchant_operations |
| agent_cash_in_issue            | agent_operations    |
| phishing_or_social_engineering | fraud_risk          |
| other                          | customer_support    |

---

## Safety Rules

The customer reply is generated with safety in mind.

The API never asks for:

```txt
PIN
OTP
password
full card number
```

It also does not promise refunds, reversals, account recovery, or unblocking. Instead, it uses safe wording such as:

```txt
Any eligible amount will be returned through official channels.
```

---

## Tech Stack

```txt
Python
FastAPI
Pydantic
Uvicorn
Vercel
```

The main decision system is rule-based. I kept it deterministic because the judge checks strict enum values, safety rules, and evidence reasoning.

---

## Models Used

By default, this project does not depend on any external LLM.

```env
LLM_MODE=off
```

The core logic is handled by rule-based classification, transaction matching, and safety templates.

There is optional Gemini support in the code for text polishing only:

```env
LLM_MODE=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

The LLM does not control important fields like `case_type`, `department`, `evidence_verdict`, or `relevant_transaction_id`.

For the deployed version, the recommended setting is:

```env
LLM_MODE=off
```

---

## Project Structure

```txt
.
├── api/
│   └── index.py
├── src/
│   ├── index.py
│   ├── models.py
│   ├── analyzer.py
│   ├── safety.py
│   ├── llm.py
│   └── utils.py
├── tests/
│   ├── test_samples.py
│   ├── smoke_test.py
│   └── generate_sample_output.py
├── sample_cases.json
├── sample_output.json
├── requirements.txt
├── vercel.json
├── README.md
├── RUNBOOK.md
└── .env.example
```

---

## Local Run

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run server:

```bash
uvicorn src.index:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

API docs:

```txt
http://127.0.0.1:8000/docs
```

---

## Testing

Run sample tests locally:

```bash
python tests/test_samples.py
```

Run sample tests against deployed API:

```bash
python tests/test_samples.py https://sust-hackathon-2-k26-8238.vercel.app
```

Expected result:

```txt
Core exact matches: 10/10
```

---

## Deployment

The project is deployed on Vercel without Docker.

Current `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index.py"
    }
  ]
}
```

The Vercel entry file is:

```txt
api/index.py
```

It imports the FastAPI app from:

```txt
src/index.py
```

---

## Known Limitations

* The system is rule-based, so unusual wording may not always be classified perfectly.
* It only uses the transaction history provided in the request.
* It does not connect to any real payment system.
* It does not perform actual refunds, reversals, settlements, or account actions.
* If evidence is unclear, it avoids guessing and returns `insufficient_data`.

---

## Submission

Live URL:

```txt
https://sust-hackathon-2-k26-8238.vercel.app
```

Repository:

```txt
https://github.com/NuhashMaq/SUST_HACKATHON_2K26
```
