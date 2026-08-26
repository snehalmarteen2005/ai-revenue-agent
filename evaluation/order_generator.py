import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Add backend directory to Python path
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models import Customer, Order, OrderItem, Product


# Make our generated dataset reproducible.
random.seed(42)


# ---------------------------------------------------------
# CUSTOMER SEGMENT BEHAVIOR
# ---------------------------------------------------------

SEGMENT_PRIMARY_CATEGORIES = {
    "student": [
        ("Laptops", 0.40),
        ("Headphones", 0.25),
        ("Mice", 0.15),
        ("Accessories", 0.20),
    ],
    "professional": [
        ("Laptops", 0.40),
        ("Keyboards", 0.20),
        ("Mice", 0.15),
        ("Accessories", 0.25),
    ],
    "gamer": [
        ("Laptops", 0.40),
        ("Headphones", 0.25),
        ("Mice", 0.20),
        ("Keyboards", 0.15),
    ],
    "mobile_user": [
        ("Phones", 0.50),
        ("Headphones", 0.20),
        ("Accessories", 0.30),
    ],
}


# ---------------------------------------------------------
# HIDDEN CROSS-SELL RELATIONSHIPS
# ---------------------------------------------------------
#
# IMPORTANT:
# These probabilities are known ONLY by the simulator.
#
# Our future recommendation engine will have to discover
# these relationships from the resulting orders.
# ---------------------------------------------------------

CROSS_SELL_RULES = {
    "Laptops": [
        ("Mice", 0.60),
        ("Accessories", 0.40),
    ],
    "Phones": [
        ("Accessories", 0.65),
        ("Headphones", 0.35),
    ],
    "Headphones": [
        ("Accessories", 0.35),
    ],
    "Mice": [
        ("Keyboards", 0.20),
    ],
    "Keyboards": [
        ("Mice", 0.25),
    ],
}


def weighted_choice(options):
    """
    Select one item from:

        [(item, probability), ...]

    The probabilities don't have to add up to exactly 1.
    """

    items = [item for item, _ in options]
    weights = [weight for _, weight in options]

    return random.choices(
        items,
        weights=weights,
        k=1,
    )[0]


def get_products_by_category(db):
    """
    Create:

        {
            "Laptops": [...],
            "Phones": [...],
            ...
        }

    so we can quickly select products.
    """

    products = db.query(Product).all()

    products_by_category = {}

    for product in products:
        products_by_category.setdefault(
            product.category,
            [],
        ).append(product)

    return products_by_category


def choose_primary_category(customer):
    """
    Decide what category this customer is most likely
    to purchase based on their segment.
    """

    segment = customer.preferences.get("segment")

    options = SEGMENT_PRIMARY_CATEGORIES.get(
        segment,
        [("Accessories", 1.0)],
    )

    return weighted_choice(options)


def add_cross_sell_products(
    primary_category,
    products_by_category,
    selected_product_ids,
):
    """
    Apply our hidden purchasing relationships.

    Example:

        Laptops
            ↓
        60% chance of Mice
        40% chance of Accessories
    """

    rules = CROSS_SELL_RULES.get(
        primary_category,
        [],
    )

    selected_products = []

    for category, probability in rules:

        if random.random() > probability:
            continue

        candidates = products_by_category.get(
            category,
            [],
        )

        if not candidates:
            continue

        product = random.choice(candidates)

        # Don't add the same product twice.
        if product.id in selected_product_ids:
            continue

        selected_products.append(product)
        selected_product_ids.add(product.id)

    return selected_products


def generate_orders(
    customer_count=100,
    orders_per_customer=5,
):
    db = SessionLocal()

    try:
        customers = (
            db.query(Customer)
            .limit(customer_count)
            .all()
        )

        if not customers:
            raise ValueError(
                "No customers found. "
                "Run customer_generator first."
            )

        products_by_category = get_products_by_category(db)

        total_orders = 0
        total_items = 0

        for customer in customers:

            for _ in range(orders_per_customer):

                # -------------------------------------------------
                # 1. Choose the customer's primary category
                # -------------------------------------------------

                primary_category = choose_primary_category(
                    customer
                )

                primary_products = products_by_category.get(
                    primary_category,
                    [],
                )

                if not primary_products:
                    continue

                primary_product = random.choice(
                    primary_products
                )

                selected_products = [
                    primary_product
                ]

                selected_product_ids = {
                    primary_product.id
                }

                # -------------------------------------------------
                # 2. Add hidden cross-sell products
                # -------------------------------------------------

                cross_sell_products = add_cross_sell_products(
                    primary_category,
                    products_by_category,
                    selected_product_ids,
                )

                selected_products.extend(
                    cross_sell_products
                )

                # -------------------------------------------------
                # 3. Calculate order total
                # -------------------------------------------------

                total_amount = Decimal("0.00")

                for product in selected_products:
                    total_amount += product.price

                # -------------------------------------------------
                # 4. Generate a realistic historical date
                # -------------------------------------------------

                days_ago = random.randint(1, 180)

                created_at = (
                    datetime.utcnow()
                    - timedelta(days=days_ago)
                )

                # -------------------------------------------------
                # 5. Create the order
                # -------------------------------------------------

                order = Order(
                    merchant_id=customer.merchant_id,
                    customer_id=customer.id,
                    total_amount=total_amount,
                    status="COMPLETED",
                    payment_status="PAID",
                    created_at=created_at,
                )

                db.add(order)
                db.flush()

                # -------------------------------------------------
                # 6. Create order items
                # -------------------------------------------------

                for product in selected_products:

                    quantity = 1

                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        price=product.price,
                    )

                    db.add(order_item)

                    total_items += 1

                total_orders += 1

        db.commit()

        print(
            f"Created {total_orders} orders "
            f"with {total_items} order items."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_orders(
        customer_count=10000,
        orders_per_customer=5,
    )