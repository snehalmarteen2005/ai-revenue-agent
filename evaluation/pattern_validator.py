import os
import sys
from collections import defaultdict
from itertools import combinations

# Add backend directory to Python path
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models import Order, OrderItem, Product


def load_order_products(db):
    """
    Build:

        {
            order_id: {product_id, product_id, ...}
        }

    Each order is represented as a set so that buying the
    same product twice doesn't count as two separate products.
    """

    order_products = defaultdict(set)

    items = db.query(OrderItem).all()

    for item in items:
        order_products[item.order_id].add(item.product_id)

    return order_products


def calculate_product_patterns(db):
    order_products = load_order_products(db)

    total_orders = len(order_products)

    if total_orders == 0:
        raise ValueError("No orders found.")

    # Number of orders containing each product.
    product_order_count = defaultdict(int)

    # Number of orders containing each product pair.
    pair_order_count = defaultdict(int)

    for products in order_products.values():

        # Count individual product appearances.
        for product_id in products:
            product_order_count[product_id] += 1

        # Count product pairs.
        for product_a, product_b in combinations(
            sorted(products),
            2,
        ):
            pair_order_count[
                (product_a, product_b)
            ] += 1

    patterns = []

    for (product_a, product_b), pair_count in pair_order_count.items():

        product_a_count = product_order_count[product_a]
        product_b_count = product_order_count[product_b]

        support = pair_count / total_orders

        confidence_a_to_b = (
            pair_count / product_a_count
        )

        confidence_b_to_a = (
            pair_count / product_b_count
        )

        product_a_probability = (
            product_a_count / total_orders
        )

        product_b_probability = (
            product_b_count / total_orders
        )

        lift = support / (
            product_a_probability
            * product_b_probability
        )

        patterns.append(
            {
                "product_a": product_a,
                "product_b": product_b,
                "pair_count": pair_count,
                "support": support,
                "confidence_a_to_b": confidence_a_to_b,
                "confidence_b_to_a": confidence_b_to_a,
                "lift": lift,
            }
        )

    return patterns


def get_product_names(db):
    products = db.query(Product).all()

    return {
        product.id: product.name
        for product in products
    }


def print_top_patterns(db, patterns, limit=20):
    product_names = get_product_names(db)

    patterns.sort(
        key=lambda x: x["lift"],
        reverse=True,
    )

    print("\n" + "=" * 80)
    print("TOP PRODUCT RELATIONSHIPS")
    print("=" * 80)

    for pattern in patterns[:limit]:

        product_a = product_names[
            pattern["product_a"]
        ]

        product_b = product_names[
            pattern["product_b"]
        ]

        print("\n----------------------------------------")

        print(
            f"{product_a}  →  {product_b}"
        )

        print(
            f"Orders together: "
            f"{pattern['pair_count']}"
        )

        print(
            f"Support: "
            f"{pattern['support']:.2%}"
        )

        print(
            f"Confidence A → B: "
            f"{pattern['confidence_a_to_b']:.2%}"
        )

        print(
            f"Confidence B → A: "
            f"{pattern['confidence_b_to_a']:.2%}"
        )

        print(
            f"Lift: "
            f"{pattern['lift']:.2f}"
        )


def main():
    db = SessionLocal()

    try:
        patterns = calculate_product_patterns(db)

        print_top_patterns(
            db,
            patterns,
            limit=20,
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()