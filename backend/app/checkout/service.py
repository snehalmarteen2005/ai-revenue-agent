from sqlalchemy.orm import Session

from app.cart.service import CartService
from app.models import Order
from app.policies.engine import PolicyEngine
from app.payments.razorpay_service import RazorpayService

class CheckoutService:

    def __init__(self, db: Session):
        self.db = db
        self.cart_service = CartService(db)
        self.policy = PolicyEngine(db)

    def prepare_checkout(
        self,
        merchant_id: int,
        customer_id: int,
    ):
        cart = self.cart_service.get_cart(
            merchant_id=merchant_id,
            customer_id=customer_id,
        )

        if not cart:
            return {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "No open cart found.",
            }

        if not cart["items"]:
            return {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "Cart is empty.",
            }

        result = self.policy.check_payment(
            merchant_id=merchant_id,
            amount=cart["total"],
            customer_id=customer_id,
        )

        return {
            "cart": cart,
            "payment_policy": result,
            "status": result["status"],
            "allowed": result["allowed"],
            "reason": result["reason"],
        }

    def confirm_checkout(
        self,
        merchant_id: int,
        customer_id: int,
    ):
        cart = self.cart_service.get_cart(
            merchant_id=merchant_id,
            customer_id=customer_id,
        )

        if not cart:
            return {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "No open cart found.",
            }

        if not cart["items"]:
            return {
                "allowed": False,
                "status": "BLOCKED",
                "reason": "Cart is empty.",
            }

        policy = self.policy.check_payment(
            merchant_id=merchant_id,
            amount=cart["total"],
            customer_id=customer_id,
        )

        if policy["status"] == "BLOCKED":
            return {
                "allowed": False,
                "status": "BLOCKED",
                "reason": policy["reason"],
            }

        razorpay = RazorpayService()

        # 1. Create Razorpay order
        razorpay_order = razorpay.create_order(
            amount_rupees=cart["total"],
            receipt=f"cart_{cart['id']}",
            customer_id=customer_id,
        )

        # 2. Create our internal order BEFORE payment
        internal_order = Order(
            merchant_id=merchant_id,
            customer_id=customer_id,
            total_amount=cart["total"],
            status="PENDING",
            payment_status="PENDING",
            razorpay_order_id=razorpay_order["id"],
        )

        self.db.add(internal_order)
        self.db.commit()
        self.db.refresh(internal_order)

        return {
            "allowed": True,
            "status": "RAZORPAY_ORDER_CREATED",
            "cart": cart,
            "order_id": internal_order.id,
            "payment": {
                "status": "RAZORPAY_ORDER_CREATED",
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "key_id": razorpay_order["key_id"],
            },
        }