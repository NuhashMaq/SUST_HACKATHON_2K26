# Runbook

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.index:app --host 0.0.0.0 --port 8000
```

## Health check

```bash
curl http://localhost:8000/health
```

## Public sample test

```bash
python tests/test_samples.py
```

## Generate sample output

```bash
python tests/generate_sample_output.py
```

## Vercel production deploy

```bash
npm install -g vercel
vercel login
vercel --prod
```

## Optional LLM env vars

```txt
LLM_MODE=gemini
GEMINI_API_KEY=<set in Vercel dashboard>
GEMINI_MODEL=gemini-2.5-flash-lite
```

Default safe mode:

```txt
LLM_MODE=off
```
