"""Local sample tester.

Run the API first:
    uvicorn src.index:app --reload

Then:
    python tests/test_samples.py
"""
import json
import sys
from pathlib import Path

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]

with open(ROOT / "sample_cases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

core_fields = [
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "human_review_required",
]

passed = 0
for case in data["cases"]:
    response = requests.post(f"{BASE_URL}/analyze-ticket", json=case["input"], timeout=20)
    print(f"\n==== {case['id']} {case['label']} ====")
    print("HTTP", response.status_code)
    if response.status_code != 200:
        print(response.text)
        continue
    actual = response.json()
    expected = case["expected_output"]
    ok = True
    for field in core_fields:
        match = actual.get(field) == expected.get(field)
        ok = ok and match
        print(f"{field}: {actual.get(field)!r} | expected {expected.get(field)!r} | {'OK' if match else 'DIFF'}")
    print("customer_reply:", actual.get("customer_reply"))
    passed += int(ok)

print(f"\nCore exact matches: {passed}/{len(data['cases'])}")
if passed != len(data["cases"]):
    sys.exit(1)
