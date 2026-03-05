import json, random, time, uuid
from datetime import datetime, timezone
from google.cloud import pubsub_v1

PROJECT_ID = "[PROJECT-ID]"
TOPIC_ID   = "transactions-stream"
TOPIC_PATH = f"projects/{PROJECT_ID}/topics/{TOPIC_ID}"

MERCHANTS = [
    ("Walmart",       "grocery"),
    ("Amazon",        "online_retail"),
    ("Shell Gas",     "fuel"),
    ("McDonalds",     "food_dining"),
    ("Best Buy",      "electronics"),
    ("Walgreens",     "pharmacy"),
    ("Delta Airlines","travel"),
    ("Netflix",       "subscription"),
    ("Uber",          "transport"),
    ("Home Depot",    "home_improvement"),
]
CARD_TYPES = ["Visa", "Mastercard", "Amex", "Discover"]
CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP"]
TX_TYPES   = ["purchase", "purchase", "purchase", "refund", "chargeback"]

publisher = pubsub_v1.PublisherClient()
print(f"Publishing to {TOPIC_PATH}")
print("Press Ctrl+C to stop")

count = 0
while True:
    merchant, category = random.choice(MERCHANTS)
    amount = round(random.uniform(1.50, 4500.00), 2)
    is_flagged = amount > 3000 or random.random() < 0.05

    tx = {
        "transaction_id":   str(uuid.uuid4()),
        "user_id":          f"user_{random.randint(1000,9999)}",
        "amount":           amount,
        "currency":         random.choice(CURRENCIES),
        "merchant_name":    merchant,
        "merchant_category":category,
        "card_type":        random.choice(CARD_TYPES),
        "transaction_type": random.choice(TX_TYPES),
        "is_flagged":       is_flagged,
        "timestamp":        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    publisher.publish(TOPIC_PATH, json.dumps(tx).encode("utf-8"))
    count += 1

    if count % 5 == 0:
        flag = "FLAGGED" if is_flagged else "       "
        print(f"  [{count:4d} sent]  {flag}  \$ {amount:8.2f}  {merchant:<20} {tx['card_type']}")

    time.sleep(1)
