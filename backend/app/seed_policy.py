from app.database import SessionLocal
from app.models import Merchant, MerchantPolicy


def seed_policy():
    db = SessionLocal()

    try:
        merchant = (
            db.query(Merchant)
            .filter(Merchant.name == "TechNova")
            .first()
        )

        if not merchant:
            raise ValueError(
                "TechNova merchant not found."
            )

        existing_policy = (
            db.query(MerchantPolicy)
            .filter(
                MerchantPolicy.merchant_id
                == merchant.id
            )
            .first()
        )

        if existing_policy:
            print("TechNova policy already exists.")
            return

        policy = MerchantPolicy(
            merchant_id=merchant.id,
            max_discount_percent=10,
            max_ai_cart_items=2,
            payment_requires_confirmation=True,
            max_payment_amount=100000,
        )

        db.add(policy)
        db.commit()

        print("TechNova policy created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_policy()