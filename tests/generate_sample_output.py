"""Generate sample_output.json without running the server."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analyzer import analyze_ticket_rule_based
from src.models import TicketRequest

with open(ROOT / "sample_cases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

outputs = []
for case in data["cases"]:
    req = TicketRequest(**case["input"])
    outputs.append({
        "id": case["id"],
        "label": case["label"],
        "output": analyze_ticket_rule_based(req),
    })

with open(ROOT / "sample_output.json", "w", encoding="utf-8") as f:
    json.dump({"outputs": outputs}, f, ensure_ascii=False, indent=2)

print(f"Wrote {ROOT / 'sample_output.json'}")
