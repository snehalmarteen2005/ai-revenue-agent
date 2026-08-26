from collections import defaultdict
from itertools import combinations

from sqlalchemy.orm import Session

from app.models import OrderItem, Product


class RevenueEngine:

    def __init__(self, db: Session):
        self.db = db

    def _load_order_products(self):
        """
        Returns:

        {
            order_id: {product_id, product_id, ...}
        }
        """

        order_products = defaultdict(set)

        items = self.db.query(OrderItem).all()

        for item in items:
            order_products[item.order_id].add(
                item.product_id
            )

        return order_products

    def get_cross_sell_candidates(
        self,
        product_id: int,
        min_confidence: float = 0.10,
        min_lift: float = 1.0,
        limit: int = 5,
    ):
        """
        Find products that are frequently purchased
        together with the requested product.
        """

        order_products = self._load_order_products()

        total_orders = len(order_products)

        if total_orders == 0:
            return []

        product_order_count = defaultdict(int)
        pair_order_count = defaultdict(int)

        # ---------------------------------------------
        # Count individual products
        # ---------------------------------------------

        for products in order_products.values():

            for pid in products:
                product_order_count[pid] += 1

            # -----------------------------------------
            # Count product pairs
            # -----------------------------------------

            for product_a, product_b in combinations(
                sorted(products),
                2,
            ):
                pair_order_count[
                    (product_a, product_b)
                ] += 1

        target_count = product_order_count.get(
            product_id,
            0,
        )

        if target_count == 0:
            return []

        candidates = []

        # ---------------------------------------------
        # Find relationships involving target product
        # ---------------------------------------------

        for (product_a, product_b), pair_count in (
            pair_order_count.items()
        ):

            if product_a != product_id and product_b != product_id:
                continue

            if product_a == product_id:
                candidate_id = product_b
            else:
                candidate_id = product_a

            candidate_count = product_order_count[
                candidate_id
            ]

            support = pair_count / total_orders

            confidence = pair_count / target_count

            target_probability = (
                target_count / total_orders
            )

            candidate_probability = (
                candidate_count / total_orders
            )

            lift = support / (
                target_probability
                * candidate_probability
            )

            if confidence < min_confidence:
                continue

            if lift < min_lift:
                continue

            candidates.append(
                {
                    "product_id": candidate_id,
                    "pair_count": pair_count,
                    "support": support,
                    "confidence": confidence,
                    "lift": lift,
                }
            )

        # ---------------------------------------------
        # Sort strongest opportunities first
        # ---------------------------------------------

        candidates.sort(
            key=lambda item: (
                item["confidence"],
                item["lift"],
            ),
            reverse=True,
        )

        candidates = candidates[:limit]

        # ---------------------------------------------
        # Add product information
        # ---------------------------------------------

        product_ids = [
            item["product_id"]
            for item in candidates
        ]

        products = (
            self.db.query(Product)
            .filter(Product.id.in_(product_ids))
            .all()
        )

        product_map = {
            product.id: product
            for product in products
        }

        results = []

        for candidate in candidates:

            product = product_map.get(
                candidate["product_id"]
            )

            if not product:
                continue

            results.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category,
                    "price": float(product.price),
                    "inventory": product.inventory,
                    "confidence": round(
                        candidate["confidence"],
                        4,
                    ),
                    "lift": round(
                        candidate["lift"],
                        4,
                    ),
                    "support": round(
                        candidate["support"],
                        4,
                    ),
                    "reason": (
                        "Frequently purchased "
                        "with this product"
                    ),
                }
            )

        return results

    def get_upsell_candidates(
        self,
        product_id: int,
        limit: int = 5,
    ):
        """
        Find higher-priced products in the same
        category as the given product (upsells).
        """

        # -----------------------------------------
        # 1. Get the source product
        # -----------------------------------------

        source = (
            self.db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if not source:
            return []

        # -----------------------------------------
        # 2. Find more expensive alternatives
        # -----------------------------------------

        candidates = (
            self.db.query(Product)
            .filter(
                Product.category == source.category,
                Product.id != product_id,
                Product.price > source.price,
                Product.active.is_(True),
                Product.inventory > 0,
            )
            .order_by(Product.price.asc())
            .limit(limit)
            .all()
        )

        # -----------------------------------------
        # 3. Build results
        # -----------------------------------------

        results = []

        for product in candidates:
            price_diff = float(product.price) - float(source.price)

            results.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category,
                    "price": float(product.price),
                    "inventory": product.inventory,
                    "price_increase": round(price_diff, 2),
                    "reason": (
                        f"Higher-tier {source.category} "
                        f"option (+₹{price_diff:.2f})"
                    ),
                }
            )

        return results