# RUNBOOK

This file explains how to run, test, and deploy the QueueStorm Investigator API.

---

## 1. Clone the Repository

```bash
git clone https://github.com/NuhashMaq/SUST_HACKATHON_2K26.git
cd SUST_HACKATHON_2K26
```

---

## 2. Create Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Linux or Mac:

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run Locally

```bash
uvicorn src.index:app --reload
```

The local server will run at:

```txt
http://127.0.0.1:8000
```

---

## 5. Check Health Endpoint

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

In PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

---

## 6. Test Analyze Endpoint

PowerShell example:

```powershell
$body = @{
  ticket_id = "TKT-TEST-001"
  complaint = "Someone called me and asked for my OTP saying my account will be blocked."
  language = "en"
  channel = "call_center"
  user_type = "customer"
  transaction_history = @()
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/analyze-ticket" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"
```

Expected important fields:

```txt
case_type             : phishing_or_social_engineering
severity              : critical
department            : fraud_risk
evidence_verdict      : insufficient_data
human_review_required : True
```

---

## 7. Swagger Docs

After running the server, open:

```txt
http://127.0.0.1:8000/docs
```

Use pure JSON in Swagger request body.

Example:

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

Do not paste PowerShell commands into Swagger.

---

## 8. Run Sample Tests

Keep the local server running, then open another terminal:

```bash
python tests/test_samples.py
```

Expected:

```txt
Core exact matches: 10/10
```

To test the live deployment:

```bash
python tests/test_samples.py https://sust-hackathon-2-k26-8238.vercel.app
```

---

## 9. Generate Sample Output

```bash
python tests/generate_sample_output.py
```

This updates:

```txt
sample_output.json
```

---

## 10. Environment Variables

Default mode:

```env
LLM_MODE=off
```

Optional Gemini mode:

```env
LLM_MODE=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

Do not commit real API keys.

---

## 11. Deploy on Vercel

This project is deployed without Docker.

Vercel uses:

```txt
api/index.py
```

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

To deploy from Vercel dashboard:

1. Import the GitHub repository.
2. Keep root directory as default or `./`.
3. Keep framework preset as `Other`.
4. Deploy.

To deploy with CLI:

```bash
npm install -g vercel
vercel login
vercel --prod
```

---

## 12. Test Live API

Health:

```powershell
Invoke-RestMethod https://sust-hackathon-2-k26-8238.vercel.app/health
```

Analyze:

```powershell
$body = @{
  ticket_id = "TKT-TEST-001"
  complaint = "Someone called me and asked for my OTP saying my account will be blocked."
  language = "en"
  channel = "call_center"
  user_type = "customer"
  transaction_history = @()
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "https://sust-hackathon-2-k26-8238.vercel.app/analyze-ticket" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"
```

---

## 13. Common Notes

`GET /` may return 404. This is normal.

`GET /analyze-ticket` may return 405. This is normal because the endpoint only accepts POST.

If Vercel shows a function pattern error, remove the `functions` block from `vercel.json`.

If Python cannot import `src`, make sure `api/index.py` contains the root path fix and imports `app` from `src.index`.

---

## 14. Final Submission

Submit this base URL:

```txt
https://sust-hackathon-2-k26-8238.vercel.app
```

Submit this repository:

```txt
https://github.com/NuhashMaq/SUST_HACKATHON_2K26
```
