import json
import requests

BASE_URL = "http://localhost:8000"

payload = {
    "ticket_id": "TKT-SMOKE-001",
    "complaint": "I paid 850 taka but it deducted twice from my account.",
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
            "status": "completed",
        },
        {
            "transaction_id": "TXN-B",
            "timestamp": "2026-04-14T08:15:42Z",
            "type": "payment",
            "amount": 850,
            "counterparty": "BILLER-DESCO",
            "status": "completed",
        },
    ],
}

print(requests.get(f"{BASE_URL}/health", timeout=10).json())
resp = requests.post(f"{BASE_URL}/analyze-ticket", json=payload, timeout=20)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
