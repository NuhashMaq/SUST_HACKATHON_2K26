# QueueStorm Investigator API

A Python FastAPI solution for the **SUST CSE Carnival 2026 · Codex Community Hackathon · QueueStorm Investigator** preliminary round.

The API classifies and investigates fintech support tickets using:

1. deterministic rule-based case classification,
2. transaction-history evidence matching,
3. strict enum-safe JSON output,
4. safety guardrails against credential requests and unauthorized refund promises,
5. optional free-tier Gemini polishing for text fields only.

The deterministic engine is the source of truth. The LLM never decides schema-critical fields.

---

## API Endpoints

### `GET /health`

Returns:

```json
{"status": "ok"}
```

### `POST /analyze-ticket`

Accepts one support ticket and returns one structured analysis object.

---

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic
- Uvicorn
- httpx for optional Gemini API calls
- Vercel Python Functions for deployment

---

## Project Structure

```txt
queue-storm-investigator/
├── src/
│   ├── __init__.py
│   ├── index.py          # FastAPI app and endpoints
│   ├── models.py         # Request/response schemas and enums
│   ├── analyzer.py       # Rule-based classifier and evidence engine
│   ├── safety.py         # Safety filters and safe templates
│   └── llm.py            # Optional Gemini text polishing
├── tests/
│   ├── generate_sample_output.py
│   ├── smoke_test.py
│   └── test_samples.py
├── sample_cases.json
├── sample_output.json
├── requirements.txt
├── vercel.json
├── Dockerfile
├── .env.example
└── README.md
```

---

## How the Analysis Works

The API follows this pipeline:

```txt
Validate input
→ Normalize complaint text
→ Extract amounts and phone-like tokens
→ Detect case_type
→ Match relevant transaction from history
→ Decide evidence_verdict
→ Assign department and severity
→ Decide human_review_required
→ Generate safe support texts
→ Optional Gemini polish of text fields
→ Final safety check
→ Return strict JSON
```

---

## Evidence Reasoning Logic

The service returns one of:

- `consistent`: transaction history supports the complaint.
- `inconsistent`: transaction history contradicts the complaint.
- `insufficient_data`: there is not enough evidence or multiple plausible transactions exist.

Examples:

- Wrong transfer + matching completed transfer = `consistent`
- Wrong transfer claim + repeated transfers to same recipient = `inconsistent`
- Multiple possible same-amount transfers = `insufficient_data`
- Phishing/OTP report with no transaction = `insufficient_data` but `critical`

---

## Supported Case Types

Exact enum values used:

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

## Department Mapping

```txt
wrong_transfer                  → dispute_resolution
payment_failed                  → payments_ops
refund_request                  → customer_support
duplicate_payment               → payments_ops
merchant_settlement_delay       → merchant_operations
agent_cash_in_issue             → agent_operations
phishing_or_social_engineering  → fraud_risk
other                           → customer_support
```

---

## Safety Guardrails

The API must never:

- ask for PIN,
- ask for OTP,
- ask for password,
- ask for full card number,
- promise a refund,
- promise a reversal,
- tell the customer to contact a suspicious third party.

Safe wording is used instead:

```txt
Please do not share your PIN, OTP, or password with anyone.
```

and:

```txt
Any eligible amount will be returned through official channels.
```

---

## Models Used

### Default mode

No external LLM is required. The default is deterministic rule-based reasoning.

```txt
LLM_MODE=off
```

Reason for default rule-based mode:

- low latency,
- no API key dependency,
- exact enum control,
- no hallucinated refund promises,
- reliable hidden-test behavior.

### Optional free LLM mode

The project supports optional Google Gemini API text polishing:

```txt
LLM_MODE=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Important: Gemini is used only to polish:

- `agent_summary`,
- `recommended_next_action`,
- `customer_reply`.

It does **not** choose:

- `case_type`,
- `department`,
- `severity`,
- `evidence_verdict`,
- `relevant_transaction_id`,
- `human_review_required`.

If Gemini fails or times out, the API returns the safe rule-based response.

---

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.index:app --reload
```

Then test:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

---

## Example Request

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-DEMO-001",
    "complaint": "I paid my electricity bill 850 taka but it deducted twice from my account.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-A",
        "timestamp": "2026-04-14T08:15:30Z",
        "type": "payment",
        "amount": 850,
        "counterparty": "BILLER-DESCO",
        "status": "completed"
      },
      {
        "transaction_id": "TXN-B",
        "timestamp": "2026-04-14T08:15:42Z",
        "type": "payment",
        "amount": 850,
        "counterparty": "BILLER-DESCO",
        "status": "completed"
      }
    ]
  }'
```

---

## Test Public Sample Cases

First run the API:

```bash
uvicorn src.index:app --reload
```

Then in another terminal:

```bash
python tests/test_samples.py
```

Generate the required sample output file:

```bash
python tests/generate_sample_output.py
```

This writes:

```txt
sample_output.json
```

---

## Vercel Deployment

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login

```bash
vercel login
```

### 3. Deploy preview

```bash
vercel
```

### 4. Deploy production

```bash
vercel --prod
```

After deployment, test:

```bash
curl https://your-project.vercel.app/health
```

and:

```bash
curl -X POST https://your-project.vercel.app/analyze-ticket \
  -H "Content-Type: application/json" \
  -d @your_test_payload.json
```

---

## Vercel Environment Variables

Default recommended deployment:

```txt
LLM_MODE=off
```

Optional Gemini mode:

```txt
LLM_MODE=gemini
GEMINI_API_KEY=your_google_ai_studio_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Add these from:

```txt
Vercel Project Dashboard → Settings → Environment Variables
```

---

## Docker Run

```bash
docker build -t queuestorm-investigator .
docker run -p 8000:8000 queuestorm-investigator
```

---

## Assumptions

- Input data is synthetic.
- No real financial action is performed.
- The API is an internal support copilot, not an autonomous decision maker.
- When evidence is ambiguous, the API returns `insufficient_data` rather than guessing.
- Human review is used for disputes, phishing, duplicate payment, agent cash-in issues, inconsistent evidence, and high-risk cases.

---

## Known Limitations

- Rule-based keyword detection may miss unusual phrasing.
- Bangla/Banglish coverage is useful but not exhaustive.
- Time matching is basic; amount/type/status matching is prioritized.
- Optional LLM mode depends on third-party free-tier availability and quota.
- The system does not connect to real payment ledgers or customer identity systems.

---

## Submission Checklist

- [x] `GET /health`
- [x] `POST /analyze-ticket`
- [x] Strict response schema
- [x] Safety guardrails
- [x] Evidence reasoning
- [x] `requirements.txt`
- [x] `vercel.json`
- [x] `.env.example`
- [x] `Dockerfile`
- [x] `README.md`
- [x] `sample_output.json`
