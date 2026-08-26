import hashlib
import hmac
import json
import os
import requests

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)


secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if not secret:
    raise RuntimeError(
        "RAZORPAY_WEBHOOK_SECRET is not configured."
    )

payload = {
    "entity": "event",
    "account_id": "test_account",
    "event": "payment.captured",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test_123",
                "order_id": "order_test_123",
                "amount": 4904200,
                "currency": "INR",
                "status": "captured",
            }
        }
    },
}

raw_body = json.dumps(
    payload,
    separators=(",", ":"),
)

signature = hmac.new(
    secret.encode(),
    raw_body.encode(),
    hashlib.sha256,
).hexdigest()

url = "http://localhost:8000/payment/webhook"

response = requests.post(
    url,
    data=raw_body,
    headers={
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
    },
)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)
