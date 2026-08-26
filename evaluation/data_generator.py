import os
import sys
import random
from decimal import Decimal

backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models import Merchant, Product


PRODUCT_TEMPLATES = {
    "Laptops": {
        "prefixes": [
            "TechNova Pro",
            "TechNova Air",
            "TechNova Student",
            "TechNova Ultra",
            "TechNova Elite",
        ],
        "suffixes": [
            "Laptop",
            "Notebook",
        ],
        "price_range": (45000, 120000),
    },

    "Phones": {
        "prefixes": [
            "TechNova X",
            "TechNova Pro",
            "TechNova Lite",
            "TechNova Max",
            "TechNova Edge",
        ],
        "suffixes": [
            "Phone",
            "Smartphone",
        ],
        "price_range": (15000, 80000),
    },

    "Headphones": {
        "prefixes": [
            "TechNova Sound",
            "TechNova Studio",
            "TechNova Bass",
            "TechNova Air",
            "TechNova Pro",
        ],
        "suffixes": [
            "Headphones",
            "Wireless Headphones",
            "ANC Headphones",
        ],
        "price_range": (1500, 12000),
    },

    "Mice": {
        "prefixes": [
            "TechNova Swift",
            "TechNova Precision",
            "TechNova Silent",
            "TechNova Gaming",
            "TechNova Ergo",
        ],
        "suffixes": [
            "Mouse",
            "Wireless Mouse",
        ],
        "price_range": (500, 5000),
    },

    "Keyboards": {
        "prefixes": [
            "TechNova Mechanical",
            "TechNova Pro",
            "TechNova Office",
            "TechNova Gaming",
            "TechNova Compact",
        ],
        "suffixes": [
            "Keyboard",
            "Mechanical Keyboard",
        ],
        "price_range": (1000, 8000),
    },

    "Accessories": {
        "prefixes": [
            "TechNova",
        ],
        "suffixes": [
            "Laptop Stand",
            "USB Hub",
            "Laptop Sleeve",
            "Phone Case",
            "Fast Charger",
            "Power Bank",
            "Cooling Pad",
            "Webcam",
            "HDMI Cable",
            "Wireless Charger",
            "Screen Protector",
            "Travel Adapter",
            "Desk Mat",
            "Cable Organizer",
        ],
        "price_range": (300, 5000),
    },
}


def get_technova():
    db = SessionLocal()

    try:
        merchant = (
            db.query(Merchant)
            .filter(Merchant.name == "TechNova")
            .first()
        )

        if not merchant:
            raise ValueError(
                "TechNova merchant not found. "
                "Run: python -m app.seed"
            )

        return merchant.id

    finally:
        db.close()


def generate_products(
    merchant_id: int,
    target_count: int = 100,
):
    db = SessionLocal()

    try:
        products = []

        product_number = 1

        while len(products) < target_count:

            category = random.choice(
                list(PRODUCT_TEMPLATES.keys())
            )

            config = PRODUCT_TEMPLATES[category]

            prefix = random.choice(
                config["prefixes"]
            )

            suffix = random.choice(
                config["suffixes"]
            )

            name = (
                f"{prefix} "
                f"{product_number} "
                f"{suffix}"
            )

            low, high = config["price_range"]

            price = Decimal(
                str(random.randint(low, high))
            )

            product = Product(
                merchant_id=merchant_id,
                name=name,
                category=category,
                description=(
                    f"{name} from TechNova."
                ),
                price=price,
                inventory=random.randint(
                    20,
                    200,
                ),
                attributes={},
                active=True,
            )

            products.append(product)

            product_number += 1

        db.add_all(products)
        db.commit()

        print(
            f"Created {len(products)} products."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    merchant_id = get_technova()

    generate_products(
        merchant_id=merchant_id,
        target_count=100,
    )