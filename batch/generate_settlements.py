import csv, uuid, random
from datetime import date

MERCHANTS  = ["Walmart","Amazon","Shell Gas","McDonalds","Best Buy",
              "Walgreens","Delta Airlines","Netflix","Uber","Home Depot"]
CARD_TYPES = ["Visa","Mastercard","Amex","Discover"]
STATUSES   = ["SETTLED"] * 85 + ["REVERSED"] * 10 + ["HELD"] * 5

rows = []
for _ in range(200):
    charged = round(random.uniform(10.00, 4500.00), 2)
    fee     = round(charged * random.uniform(0.015, 0.029), 2)
    status  = random.choice(STATUSES)
    settled = charged if status == "SETTLED" else 0.00
    rows.append({
        "settlement_id":     str(uuid.uuid4()),
        "transaction_id":    str(uuid.uuid4()),
        "settled_amount":    settled,
        "fee_amount":        fee if status == "SETTLED" else 0.00,
        "net_amount":        round(settled - fee, 2) if status == "SETTLED" else 0.00,
        "settlement_status": status,
        "settlement_date":   str(date.today()),
        "bank_reference":    f"BNK-{random.randint(100000,999999)}",
        "merchant_name":     random.choice(MERCHANTS),
        "card_type":         random.choice(CARD_TYPES),
    })

fname = "settlements_daily.csv"
with open(fname, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

settled   = sum(1 for r in rows if r["settlement_status"] == "SETTLED")
reversed_ = sum(1 for r in rows if r["settlement_status"] == "REVERSED")
held      = sum(1 for r in rows if r["settlement_status"] == "HELD")
total     = sum(r["net_amount"] for r in rows)
print(f"Generated {len(rows)} records -> {fname}")
print(f"  SETTLED:   {settled}")
print(f"  REVERSED:  {reversed_}")
print(f"  HELD:      {held}")
print(f"  Total net: \")
