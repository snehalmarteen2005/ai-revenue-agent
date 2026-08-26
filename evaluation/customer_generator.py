import os
import sys
import random

# Add backend directory to Python path
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models import Merchant, Customer


FIRST_NAMES = [
    "Aarav",
    "Arjun",
    "Rahul",
    "Rohan",
    "Aditya",
    "Karan",
    "Vikram",
    "Ananya",
    "Priya",
    "Sneha",
    "Meera",
    "Isha",
    "Kavya",
    "Neha",
    "Pooja",
]

LAST_NAMES = [
    "Sharma",
    "Patel",
    "Reddy",
    "Kumar",
    "Singh",
    "Mehta",
    "Nair",
    "Rao",
    "Verma",
    "Joshi",
]


CUSTOMER_SEGMENTS = {
    "student": {
        "preferences": [
            "Laptops",
            "Headphones",
            "Mice",
            "Accessories",
        ],
        "price_sensitivity": "high",
    },
    "professional": {
        "preferences": [
            "Laptops",
            "Keyboards",
            "Mice",
            "Accessories",
        ],
        "price_sensitivity": "medium",
    },
    "gamer": {
        "preferences": [
            "Laptops",
            "Headphones",
            "Mice",
            "Keyboards",
        ],
        "price_sensitivity": "low",
    },
    "mobile_user": {
        "preferences": [
            "Phones",
            "Headphones",
            "Accessories",
        ],
        "price_sensitivity": "medium",
    },
}


def get_technova_id():
    db = SessionLocal()

    try:
        merchant = (
            db.query(Merchant)
            .filter(Merchant.name == "TechNova")
            .first()
        )

        if not merchant:
            raise ValueError(
                "TechNova merchant not found. Run: python -m app.seed"
            )

        return merchant.id

    finally:
        db.close()


def generate_customers(merchant_id: int, count: int = 100):
    db = SessionLocal()

    try:
        customers = []

        for i in range(count):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)

            name = f"{first_name} {last_name}"

            # Ensure every generated email is unique.
            email = f"customer{i + 1}@technova.example"

            segment = random.choice(
                list(CUSTOMER_SEGMENTS.keys())
            )

            segment_data = CUSTOMER_SEGMENTS[segment]

            preferences = {
                "segment": segment,
                "interests": segment_data["preferences"],
                "price_sensitivity": segment_data[
                    "price_sensitivity"
                ],
            }

            customer = Customer(
                merchant_id=merchant_id,
                name=name,
                email=email,
                preferences=preferences,
            )

            customers.append(customer)

        db.add_all(customers)
        db.commit()

        print(f"Created {count} customers.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    merchant_id = get_technova_id()
    generate_customers(
    merchant_id,
    count=10000,
)