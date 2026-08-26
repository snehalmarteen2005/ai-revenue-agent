from decimal import Decimal

from app.database import SessionLocal
from app.models import Merchant, Product


def seed_database():
    db = SessionLocal()

    try:
        merchant = Merchant(
            name="TechNova",
            description="Online electronics and accessories store",
        )

        db.add(merchant)
        db.flush()

        products = [
            Product(
                merchant_id=merchant.id,
                name="TechNova Pro Laptop",
                category="Laptops",
                description="16GB RAM laptop designed for programming and college use.",
                price=Decimal("59999.00"),
                inventory=25,
                attributes={
                    "ram": "16GB",
                    "storage": "512GB SSD",
                    "processor": "Ryzen 7",
                    "weight": "1.5kg",
                },
            ),
            Product(
                merchant_id=merchant.id,
                name="TechNova Wireless Mouse",
                category="Mice",
                description="Lightweight wireless mouse for everyday productivity.",
                price=Decimal("999.00"),
                inventory=100,
                attributes={
                    "connection": "Wireless",
                    "weight": "85g",
                    "battery": "12 months",
                },
            ),
            Product(
                merchant_id=merchant.id,
                name="TechNova Laptop Stand",
                category="Accessories",
                description="Adjustable aluminum laptop stand.",
                price=Decimal("1999.00"),
                inventory=60,
                attributes={
                    "material": "Aluminum",
                    "adjustable": True,
                },
            ),
            Product(
                merchant_id=merchant.id,
                name="TechNova ANC Headphones",
                category="Headphones",
                description="Wireless headphones with active noise cancellation.",
                price=Decimal("2499.00"),
                inventory=75,
                attributes={
                    "battery": "40 hours",
                    "noise_cancellation": True,
                    "weight": "180g",
                },
            ),
        ]

        db.add_all(products)
        db.commit()

        print("TechNova database seeded successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()