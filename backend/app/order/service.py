from sqlalchemy.orm import Session

from app.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    Product,
)


class OrderService:

    def __init__(self, db: Session):
        self.db = db

    def create_order_from_cart(
        self,
        merchant_id: int,
        customer_id: int,
        cart: dict,
        razorpay_order_id: str,
        razorpay_payment_id: str,
    ):
        """
        Finalize the existing internal order after
        successful Razorpay payment verification.
        """

        # Find the order that was created during checkout.
        order = (
            self.db.query(Order)
            .filter(
                Order.razorpay_order_id
                == razorpay_order_id
            )
            .first()
        )

        if not order:
            raise ValueError(
                "Internal order not found for "
                f"Razorpay order {razorpay_order_id}"
            )

        # If this payment was already processed,
        # return the existing order.
        if (
            order.payment_status == "PAID"
            and order.razorpay_payment_id
            == razorpay_payment_id
        ):
            return order

        # Update the existing order.
        order.razorpay_payment_id = (
            razorpay_payment_id
        )
        order.status = "CONFIRMED"
        order.payment_status = "PAID"

        # Check whether OrderItems already exist.
        existing_items = (
            self.db.query(OrderItem)
            .filter(
                OrderItem.order_id == order.id
            )
            .count()
        )

        # Only create OrderItems once.
        if existing_items == 0:

            cart_items = (
                self.db.query(CartItem)
                .filter(
                    CartItem.cart_id == cart["id"]
                )
                .all()
            )

            for cart_item in cart_items:

                product = (
                    self.db.query(Product)
                    .filter(
                        Product.id == cart_item.product_id
                    )
                    .first()
                )

                if not product:
                    raise ValueError(
                        f"Product {cart_item.product_id} not found."
                    )

                if product.inventory < cart_item.quantity:
                    raise ValueError(
                        f"Insufficient inventory for "
                        f"product {product.id}."
                    )

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.unit_price,
                )

                self.db.add(order_item)

                # Reduce inventory after successful payment
                product.inventory -= cart_item.quantity

        self.db.commit()
        self.db.refresh(order)

        return order

    def mark_cart_checked_out(
        self,
        cart_id: int,
    ):
        """
        Mark the cart as checked out after
        successful payment.
        """

        cart = (
            self.db.query(Cart)
            .filter(Cart.id == cart_id)
            .first()
        )

        if not cart:
            return None

        cart.status = "CHECKED_OUT"

        self.db.commit()
        self.db.refresh(cart)

        return cart

    def get_order_status(
        self,
        merchant_id: int,
        customer_id: int,
        order_id: int | None = None,
    ):
        """
        Get the customer's order status and items.
        """

        query = (
            self.db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                Order.customer_id == customer_id,
            )
        )

        if order_id is not None:
            query = query.filter(
                Order.id == order_id
            )

        order = (
            query
            .order_by(Order.id.desc())
            .first()
        )

        if not order:
            return {
                "found": False,
                "message": "No order found.",
            }

        order_items = (
            self.db.query(OrderItem)
            .filter(
                OrderItem.order_id == order.id
            )
            .all()
        )

        items = []

        for item in order_items:
            product = (
                self.db.query(Product)
                .filter(Product.id == item.product_id)
                .first()
            )

            items.append({
                "product_id": item.product_id,
                "product_name": (
                    product.name
                    if product
                    else "Unknown product"
                ),
                "quantity": item.quantity,
                "price": float(item.price),
            })

        return {
            "found": True,
            "order_id": order.id,
            "customer_id": order.customer_id,
            "total_amount": float(order.total_amount),
            "status": order.status,
            "payment_status": order.payment_status,
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_id": order.razorpay_payment_id,
            "items": items,
        }

    def get_order_history(
        self,
        merchant_id: int,
        customer_id: int,
        limit: int = 10,
    ):
        """
        Return the customer's most recent orders
        with their purchased products.
        """

        orders = (
            self.db.query(Order)
            .filter(
                Order.merchant_id == merchant_id,
                Order.customer_id == customer_id,
            )
            .order_by(Order.id.desc())
            .limit(limit)
            .all()
        )

        result = []

        for order in orders:

            order_items = (
                self.db.query(OrderItem)
                .filter(
                    OrderItem.order_id == order.id
                )
                .all()
            )

            items = []

            for item in order_items:

                product = (
                    self.db.query(Product)
                    .filter(
                        Product.id == item.product_id
                    )
                    .first()
                )

                items.append({
                    "product_id": item.product_id,
                    "product_name": (
                        product.name
                        if product
                        else "Unknown product"
                    ),
                    "quantity": item.quantity,
                    "price": float(item.price),
                })

            result.append({
                "order_id": order.id,
                "total_amount": float(
                    order.total_amount
                ),
                "status": order.status,
                "payment_status": order.payment_status,
                "items": items,
            })

        if not result:
            return {
                "found": False,
                "message": "No previous orders found.",
            }

        lines = ["Here are your previous orders:"]

        for index, order in enumerate(result, start=1):
            lines.append(
                f"{index}. Order ID: {order['order_id']} "
                f"- Amount: ₹{order['total_amount']:.2f} "
                f"- Status: {order['status']} "
                f"- Payment Status: {order['payment_status']}"
            )

            if order["items"]:
                for item in order["items"]:
                    lines.append(
                        f"   - {item['product_name']} "
                        f"(Quantity: {item['quantity']}, "
                        f"Price: ₹{item['price']:.2f})"
                    )

        return {
            "found": True,
            "message": "\n".join(lines),
        }
