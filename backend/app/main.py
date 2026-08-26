import json
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.policies.engine import PolicyEngine
from app.database import Base, engine, get_db
from app.models import Merchant, Product
from app.recommendations.engine import RevenueEngine
from app.models import AuditEvent
from app.agent import RevenueAgent
from pydantic import BaseModel
from app.payments.razorpay_service import RazorpayService
from fastapi.middleware.cors import CORSMiddleware
Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="AI Revenue Agent",
    description="AI-powered merchant revenue optimization platform",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class AgentRequest(BaseModel):
    customer_id: int
    message: str

@app.get("/")
def root():
    return {
        "message": "AI Revenue Agent API is running",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/health/database")
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "database": "connected",
    }
@app.get("/products/{product_id}/cross-sells")
def get_cross_sells(
    product_id: int,
    db: Session = Depends(get_db),
):
    engine = RevenueEngine(db)

    recommendations = engine.get_cross_sell_candidates(
        product_id=product_id,
    )

    return {
        "product_id": product_id,
        "recommendations": recommendations,
    }
@app.get("/policy/{merchant_id}/discount")
def check_discount(
    merchant_id: int,
    discount_percent: float,
    db: Session = Depends(get_db),
):
    engine = PolicyEngine(db)

    return engine.check_discount(
        merchant_id=merchant_id,
        discount_percent=discount_percent,
    )
@app.get("/policy/{merchant_id}/payment")
def check_payment(
    merchant_id: int,
    amount: float,
    db: Session = Depends(get_db),
):
    engine = PolicyEngine(db)

    return engine.check_payment(
        merchant_id=merchant_id,
        amount=amount,
    )
@app.get("/audit")
def get_audit_events(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.merchant_id == merchant_id
        )
        .order_by(
            AuditEvent.created_at.desc()
        )
        .limit(100)
        .all()
    )

    return [
        {
            "id": event.id,
            "customer_id": event.customer_id,
            "action": event.action,
            "status": event.status,
            "reason": event.reason,
            "metadata": event.event_metadata,
            "created_at": event.created_at,
        }
        for event in events
    ]
@app.get("/agent/laptop")
def laptop_agent(
    max_price: float,
    customer_id: int = 0,
    db: Session = Depends(get_db),
):
    agent = RevenueAgent(
        db=db,
        merchant_id=1,
        customer_id=customer_id,
    )

    response = agent.chat(
        f"Show me laptops under {max_price} rupees"
    )

    return {"response": response}
@app.post("/agent/chat")
def agent_chat(
    request: AgentRequest,
    db: Session = Depends(get_db),
):
    agent = RevenueAgent(
        db=db,
        merchant_id=1,
        customer_id=request.customer_id,
    )

    return agent.chat(request.message)

@app.post("/payment/verify")
def verify_payment(
    payment_data: dict,
    db: Session = Depends(get_db),
):
    razorpay = RazorpayService()

    # 1. Verify the Razorpay signature
    result = razorpay.verify_payment(
        razorpay_order_id=payment_data["razorpay_order_id"],
        razorpay_payment_id=payment_data["razorpay_payment_id"],
        razorpay_signature=payment_data["razorpay_signature"],
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["reason"],
        )

    # 2. Get the customer and merchant
    customer_id = payment_data["customer_id"]
    merchant_id = 1

    # 3. Get the customer's open cart
    from app.tools.cart import get_cart

    cart = get_cart(
        db=db,
        merchant_id=merchant_id,
        customer_id=customer_id,
    )

    if not cart or not cart.get("cart"):
        raise HTTPException(
            status_code=404,
            detail="Open cart not found.",
        )

    cart_data = cart["cart"]

    # 4. Create our internal order
    from app.order.service import OrderService

    order_service = OrderService(db)

    order = order_service.create_order_from_cart(
        merchant_id=merchant_id,
        customer_id=customer_id,
        cart=cart_data,
        razorpay_order_id=result["order_id"],
        razorpay_payment_id=result["payment_id"],
    )

    # 5. Mark cart as checked out
    order_service.mark_cart_checked_out(
        cart_id=cart_data["id"],
    )

    return {
        "success": True,
        "status": "PAYMENT_SUCCESS",
        "order_id": order.id,
        "payment_id": result["payment_id"],
        "razorpay_order_id": result["order_id"],
        "amount": float(order.total_amount),
        "currency": "INR",
    }

@app.post("/payment/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    razorpay = RazorpayService()

    # 1. Read the exact raw webhook body
    payload = await request.body()

    # 2. Get Razorpay signature
    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature.",
        )

    # 3. Get webhook secret
    webhook_secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET"
    )

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_WEBHOOK_SECRET is not configured.",
        )

    # 4. Verify webhook signature
    if not razorpay.verify_webhook_signature(
        payload.decode("utf-8"),
        signature,
        webhook_secret,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature.",
        )

    # 5. Parse verified event
    event = json.loads(
        payload.decode("utf-8")
    )

    event_name = event.get("event")

    print(
        "RAZORPAY WEBHOOK EVENT:",
        event_name,
    )

    # --------------------------------------------------
    # PAYMENT CAPTURED
    # --------------------------------------------------

    if event_name == "payment.captured":

        payment_entity = (
            event
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        razorpay_payment_id = payment_entity.get(
            "id"
        )

        razorpay_order_id = payment_entity.get(
            "order_id"
        )

        if not razorpay_payment_id:
            raise HTTPException(
                status_code=400,
                detail="Missing Razorpay payment ID.",
            )

        if not razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Missing Razorpay order ID.",
            )

        # Find our internal order using the
        # Razorpay order ID.
        from app.models import Order

        order = (
            db.query(Order)
            .filter(
                Order.razorpay_order_id
                == razorpay_order_id
            )
            .first()
        )

        if not order:
            print(
                "No internal order found for Razorpay "
                f"order {razorpay_order_id}"
            )

            # Return 200 so Razorpay doesn't repeatedly
            # retry an event that we cannot process.
            return {
                "success": True,
                "status": "ORDER_NOT_FOUND",
            }

        # Idempotency:
        # If this payment was already processed,
        # don't process it again.
        if (
            order.payment_status == "PAID"
            and order.razorpay_payment_id
            == razorpay_payment_id
        ):
            return {
                "success": True,
                "status": "ALREADY_PROCESSED",
                "order_id": order.id,
            }

        # Update payment information.
        order.razorpay_payment_id = (
            razorpay_payment_id
        )

        order.payment_status = "PAID"
        order.status = "CONFIRMED"

        from app.models import Cart, CartItem, OrderItem, Product

        # Find the cart used for this order
        cart = (
            db.query(Cart)
            .filter(
                Cart.customer_id == order.customer_id,
                Cart.status == "OPEN",
            )
            .order_by(Cart.id.desc())
            .first()
        )

        if cart:
            cart_items = (
                db.query(CartItem)
                .filter(
                    CartItem.cart_id == cart.id
                )
                .all()
            )

            # Only create items/inventory changes once
            existing_item = (
                db.query(OrderItem)
                .filter(
                    OrderItem.order_id == order.id
                )
                .first()
            )

            if not existing_item:
                for cart_item in cart_items:

                    product = (
                        db.query(Product)
                        .filter(
                            Product.id
                            == cart_item.product_id
                        )
                        .first()
                    )

                    if not product:
                        raise HTTPException(
                            status_code=404,
                            detail=(
                                f"Product "
                                f"{cart_item.product_id} not found."
                            ),
                        )

                    if product.inventory < cart_item.quantity:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Insufficient inventory for "
                                f"product {product.id}."
                            ),
                        )

                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=cart_item.product_id,
                        quantity=cart_item.quantity,
                        price=cart_item.unit_price,
                    )

                    db.add(order_item)

                    product.inventory -= cart_item.quantity

                cart.status = "CHECKED_OUT"

        db.commit()
        db.refresh(order)

        print(
            "ORDER PAYMENT UPDATED:",
            order.id,
            "PAID",
        )

        return {
            "success": True,
            "status": "PAYMENT_UPDATED",
            "order_id": order.id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
        }

    # --------------------------------------------------
    # ORDER PAID
    # --------------------------------------------------

    if event_name == "order.paid":

        order_entity = (
            event
            .get("payload", {})
            .get("order", {})
            .get("entity", {})
        )

        razorpay_order_id = order_entity.get(
            "id"
        )

        if not razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Missing Razorpay order ID.",
            )

        from app.models import Order

        order = (
            db.query(Order)
            .filter(
                Order.razorpay_order_id
                == razorpay_order_id
            )
            .first()
        )

        if not order:
            return {
                "success": True,
                "status": "ORDER_NOT_FOUND",
            }

        # Don't overwrite an already-paid order.
        if order.payment_status != "PAID":
            order.payment_status = "PAID"
            order.status = "CONFIRMED"

            db.commit()
            db.refresh(order)

        return {
            "success": True,
            "status": "ORDER_MARKED_PAID",
            "order_id": order.id,
        }

    # --------------------------------------------------
    # PAYMENT FAILED
    # --------------------------------------------------

    if event_name == "payment.failed":

        payment_entity = (
            event
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        razorpay_order_id = payment_entity.get(
            "order_id"
        )

        if razorpay_order_id:

            from app.models import Order

            order = (
                db.query(Order)
                .filter(
                    Order.razorpay_order_id
                    == razorpay_order_id
                )
                .first()
            )

            if order:
                order.payment_status = "FAILED"

                db.commit()
                db.refresh(order)

                print(
                    "ORDER PAYMENT FAILED:",
                    order.id,
                )

                return {
                    "success": True,
                    "status": "PAYMENT_FAILED",
                    "order_id": order.id,
                }

    # Other enabled events that we don't need to
    # modify the database for.
    return {
        "success": True,
        "status": "EVENT_RECEIVED",
        "event": event_name,
    }
