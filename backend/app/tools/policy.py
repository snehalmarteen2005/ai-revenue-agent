from sqlalchemy.orm import Session

from app.policies.engine import PolicyEngine


def check_discount_policy(
    db: Session,
    merchant_id: int,
    discount_percent: float,
    customer_id: int | None = None,
):
    engine = PolicyEngine(db)

    return engine.check_discount(
        merchant_id=merchant_id,
        discount_percent=discount_percent,
        customer_id=customer_id,
    )


def check_payment_policy(
    db: Session,
    merchant_id: int,
    amount: float,
    customer_id: int | None = None,
):
    engine = PolicyEngine(db)

    return engine.check_payment(
        merchant_id=merchant_id,
        amount=amount,
        customer_id=customer_id,
    )