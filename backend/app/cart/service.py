from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Cart, CartItem, Product


class CartService:

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_cart(
        self,
        merchant_id: int,
        customer_id: int,
    ):
        cart = (
            self.db.query(Cart)
            .filter(
                Cart.merchant_id == merchant_id,
                Cart.customer_id == customer_id,
                Cart.status == "OPEN",
            )
            .first()
        )

        if cart:
            return cart

        cart = Cart(
            merchant_id=merchant_id,
            customer_id=customer_id,
            status="OPEN",
            subtotal=0,
            discount=0,
            total=0,
        )

        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)

        return cart

    def add_item(
        self,
        merchant_id: int,
        customer_id: int,
        product_id: int,
        quantity: int = 1,
    ):
        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        product = (
            self.db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if not product:
            raise ValueError(
                "Product not found."
            )

        if not product.active:
            raise ValueError(
                "Product is not active."
            )

        if product.inventory < quantity:
            raise ValueError(
                f"Only {product.inventory} units "
                f"are available."
            )

        cart = self.get_or_create_cart(
            merchant_id=merchant_id,
            customer_id=customer_id,
        )

        item = (
            self.db.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
            .first()
        )

        if item:
            new_quantity = item.quantity + quantity

            if product.inventory < new_quantity:
                raise ValueError(
                    f"Only {product.inventory} units "
                    f"are available."
                )

            item.quantity = new_quantity

            item.total_price = (
                Decimal(str(item.unit_price))
                * new_quantity
            )

        else:
            unit_price = Decimal(
                str(product.price)
            )

            item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=(
                    unit_price * quantity
                ),
            )

            self.db.add(item)

        self.db.flush()

        self.recalculate(cart)

        self.db.commit()
        self.db.refresh(cart)

        return cart

    def recalculate(self, cart: Cart):

        items = (
            self.db.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id
            )
            .all()
        )

        subtotal = sum(
            (
                Decimal(str(item.total_price))
                for item in items
            ),
            Decimal("0"),
        )

        discount = Decimal(
            str(cart.discount or 0)
        )

        total = subtotal - discount

        if total < 0:
            total = Decimal("0")

        cart.subtotal = subtotal
        cart.total = total

    def get_cart(
        self,
        merchant_id: int,
        customer_id: int,
    ):
        cart = (
            self.db.query(Cart)
            .filter(
                Cart.merchant_id == merchant_id,
                Cart.customer_id == customer_id,
                Cart.status == "OPEN",
            )
            .first()
        )

        if not cart:
            return None

        items = (
            self.db.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id
            )
            .all()
        )

        cart_items = []

        for item in items:

            product = (
                self.db.query(Product)
                .filter(
                    Product.id == item.product_id
                )
                .first()
            )

            cart_items.append(
                {
                    "product_id": item.product_id,
                    "product_name": (
                        product.name
                        if product
                        else "Unknown product"
                    ),
                    "quantity": item.quantity,
                    "unit_price": float(
                        item.unit_price
                    ),
                    "total_price": float(
                        item.total_price
                    ),
                }
            )

        return {
            "id": cart.id,
            "merchant_id": cart.merchant_id,
            "customer_id": cart.customer_id,
            "status": cart.status,
            "subtotal": float(cart.subtotal),
            "discount": float(cart.discount),
            "total": float(cart.total),
            "items": cart_items,
        }