from sqlalchemy.orm import Session

from app.cart.service import CartService


def add_to_cart(
    db: Session,
    merchant_id: int,
    customer_id: int,
    product_id: int,
    quantity: int = 1,
):
    service = CartService(db)

    service.add_item(
        merchant_id=merchant_id,
        customer_id=customer_id,
        product_id=product_id,
        quantity=quantity,
    )

    cart = service.get_cart(
        merchant_id=merchant_id,
        customer_id=customer_id,
    )

    if not cart:
        return {
            "success": False,
            "action": "ADD_TO_CART",
            "reason": "Cart not found after adding item.",
        }

    added_item = next(
        (
            item
            for item in cart["items"]
            if item["product_id"] == product_id
        ),
        None,
    )

    if not added_item:
        return {
            "success": False,
            "action": "ADD_TO_CART",
            "reason": "Product was not found in the cart after the operation.",
        }

    return {
        "success": True,
        "action": "ADD_TO_CART",
        "product": {
            "id": product_id,
            "quantity": added_item["quantity"],
            "unit_price": added_item["unit_price"],
            "total_price": added_item["total_price"],
        },
        "cart_total": cart["total"],
        "currency": "INR",
    }
def get_cart(
    db: Session,
    merchant_id: int,
    customer_id: int,
):
    """
    Get the customer's current cart.

    This is read-only and does not modify
    the cart.
    """

    service = CartService(db)

    cart = service.get_cart(
        merchant_id=merchant_id,
        customer_id=customer_id,
    )

    if not cart:
        return {
            "success": False,
            "cart": None,
            "reason": "No cart found.",
        }

    return {
        "success": True,
        "cart": cart,
        "currency": "INR",
    }