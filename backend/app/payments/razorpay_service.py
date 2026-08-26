import os

import razorpay


class RazorpayService:

    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not key_id:
            raise RuntimeError(
                "RAZORPAY_KEY_ID is not configured."
            )

        if not key_secret:
            raise RuntimeError(
                "RAZORPAY_KEY_SECRET is not configured."
            )

        self.key_id = key_id

        self.client = razorpay.Client(
            auth=(key_id, key_secret)
        )

    def create_order(
        self,
        amount_rupees: float,
        receipt: str,
        customer_id: int,
    ):
        amount_paise = int(
            round(amount_rupees * 100)
        )

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "customer_id": str(customer_id),
                "source": "ai_revenue_agent",
            },
        }

        order = self.client.order.create(  # type: ignore[attr-defined]
            data=order_data
        )

        return {
            "id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "status": order["status"],
            "receipt": order["receipt"],
            "key_id": self.key_id,
        }

    def verify_payment(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ):
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )

            return {
                "success": True,
                "status": "PAYMENT_SIGNATURE_VERIFIED",
                "order_id": razorpay_order_id,
                "payment_id": razorpay_payment_id,
            }

        except Exception:
            return {
                "success": False,
                "status": "PAYMENT_VERIFICATION_FAILED",
                "reason": "Invalid Razorpay payment signature.",
            }

    def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        webhook_secret: str,
    ):
        try:
            self.client.utility.verify_webhook_signature(
                payload,
                signature,
                webhook_secret,
            )

            return True

        except Exception:
            return False