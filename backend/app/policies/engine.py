from sqlalchemy.orm import Session

from app.models import MerchantPolicy
from app.audit.service import AuditService

class PolicyEngine:

    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def get_policy(
        self,
        merchant_id: int,
    ):
        return (
            self.db.query(MerchantPolicy)
            .filter(
                MerchantPolicy.merchant_id
                == merchant_id
            )
            .first()
        )

    def check_discount(
        self,
        merchant_id: int,
        discount_percent: float,
        customer_id: int | None = None,
    ):
        policy = self.get_policy(merchant_id)

        if not policy:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "No merchant policy found.",
            }

        elif discount_percent < 0:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "Discount cannot be negative.",
            }

        elif discount_percent > policy.max_discount_percent:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": (
                    f"Requested discount of "
                    f"{discount_percent}% exceeds "
                    f"merchant limit of "
                    f"{policy.max_discount_percent}%."
                ),
            }

        else:
            result = {
                "allowed": True,
                "status": "ALLOWED",
                "reason": (
                    "Discount is within merchant policy."
                ),
            }

        self.audit.record(
            merchant_id=merchant_id,
            customer_id=customer_id,
            action="DISCOUNT",
            reason=result["reason"],
            status=result["status"],
            metadata={
                "requested_discount_percent": discount_percent,
                "allowed_discount_percent": (
                    policy.max_discount_percent
                    if policy
                    else None
                ),
            },
        )

        return result

    def check_payment(
        self,
        merchant_id: int,
        amount: float,
        customer_id: int | None = None,
    ):
        policy = self.get_policy(merchant_id)

        if not policy:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "No merchant policy found.",
            }

        elif amount <= 0:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": (
                    "Payment amount must be greater than zero."
                ),
            }

        elif amount > policy.max_payment_amount:
            result = {
                "allowed": False,
                "status": "BLOCKED",
                "reason": (
                    f"Payment of ₹{amount:.2f} "
                    f"exceeds merchant limit of "
                    f"₹{policy.max_payment_amount:.2f}."
                ),
            }

        elif policy.payment_requires_confirmation:
            result = {
                "allowed": False,
                "status": "CONFIRMATION_REQUIRED",
                "reason": (
                    "Customer confirmation is required "
                    "before payment."
                ),
            }

        else:
            result = {
                "allowed": True,
                "status": "ALLOWED",
                "reason": (
                    "Payment satisfies merchant policy."
                ),
            }

        self.audit.record(
            merchant_id=merchant_id,
            customer_id=customer_id,
            action="PAYMENT",
            reason=result["reason"],
            status=result["status"],
            metadata={
                "requested_amount": amount,
                "maximum_payment_amount": (
                    policy.max_payment_amount
                    if policy
                    else None
                ),
                "confirmation_required": (
                    policy.payment_requires_confirmation
                    if policy
                    else None
                ),
            },
        )

        return result