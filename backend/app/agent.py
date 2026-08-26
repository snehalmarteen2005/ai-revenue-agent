import json

import ollama
from sqlalchemy.orm import Session

from app.tools.catalog import (
    search_products,
    resolve_product,
)
from app.tools.revenue import (
    get_cross_sells,
    get_upsells,
)
from app.tools.policy import (
    check_discount_policy,
    check_payment_policy,
)
from app.tools.cart import (
    add_to_cart,
    get_cart,
)
from app.checkout.service import CheckoutService
from app.order.service import OrderService

class RevenueAgent:

    def __init__(
        self,
        db: Session,
        merchant_id: int,
        customer_id: int,
    ):
        self.db = db
        self.merchant_id = merchant_id
        self.customer_id = customer_id
        self.model = "qwen2.5:3b"
        self.mutation_executed = False
    # -----------------------------------=--------------
    # TOOLS AVAILABLE TO QWEN
    # -------------------------------------------------

    def get_tools(self):

        return [
            {
    "type": "function",
    "function": {
        "name": "prepare_checkout",
        "description": (
            "Prepare the customer's current cart "
            "for checkout. This checks the merchant "
            "payment policy but does NOT make a payment."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "get_cart",
        "description": (
            "Get the customer's current cart. "
            "Use this whenever the customer asks "
            "what is in their cart, their cart total, "
            "or wants to review their cart. "
            "This tool is read-only and does not modify "
            "the cart."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": (
            "Get the customer's order status. "
            "Use this when the customer asks about "
            "their order, payment status, or order details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": (
                        "Optional internal order ID. "
                        "If omitted, return the customer's "
                        "most recent order."
                    ),
                }
            },
            "required": [],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "get_order_history",
        "description": (
            "Get the customer's recent orders. "
            "Use this when the customer asks to see "
            "previous orders, order history, past purchases, "
            "or recent orders."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of recent orders "
                        "to return. Default is 10."
                    ),
                }
            },
            "required": [],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "resolve_product",
        "description": (
            "Find the exact real TechNova product "
            "matching a product name. Use this "
            "before adding a product to the cart "
            "when the customer provides a product "
            "name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": (
                        "The exact or natural-language "
                        "name of the product."
                    ),
                }
            },
            "required": ["product_name"],
        },
    },
},
            {
                "type": "function",
                "function": {
                    "name": "search_products",
                    "description": (
                        "Search TechNova's real product "
                        "catalog. Use this whenever the "
                        "customer asks about products."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "Product name or "
                                    "search term."
                                ),
                            },
                            "category": {
                                "type": "string",
                                "description": (
                                    "Product category such "
                                    "as Laptops, Phones, "
                                    "Headphones, Mice, "
                                    "Keyboards, Accessories."
                                ),
                            },
                            "max_price": {
                                "type": "number",
                                "description": (
                                    "Maximum price the "
                                    "customer wants to pay."
                                ),
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cross_sells",
                    "description": (
                        "Find products that are frequently "
                        "purchased together with a product."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "integer",
                                "description": (
                                    "ID of the product."
                                ),
                            },
                        },
                        "required": ["product_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_upsells",
                    "description": (
                        "Find higher-priced alternatives "
                        "in the same product category."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "integer",
                                "description": (
                                    "ID of the product."
                                ),
                            },
                        },
                        "required": ["product_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_discount_policy",
                    "description": (
                        "Check whether a requested "
                        "discount is allowed by "
                        "the merchant policy."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "discount_percent": {
                                "type": "number",
                            },
                        },
                        "required": [
                            "discount_percent"
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_payment_policy",
                    "description": (
                        "Check whether a proposed payment "
                        "is allowed. This does NOT execute "
                        "the payment."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                            },
                        },
                        "required": ["amount"],
                    },
                },
            },
{
    "type": "function",
    "function": {
        "name": "add_to_cart",
        "description": (
            "Add ONE or more units of a VERIFIED "
            "TechNova product to the customer's cart. "
            "Only call this after the product has been "
            "identified by search_products or "
            "resolve_product. NEVER guess a product ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": (
                        "Verified database product ID "
                        "returned by another tool."
                    ),
                },
                "quantity": {
                    "type": "integer",
                    "description": (
                        "Number of units. Default is 1."
                    ),
                },
            },
            "required": ["product_id"],
        },
    },
},
            {
    "type": "function",
    "function": {
        "name": "confirm_checkout",
        "description": (
            "Confirm the customer's current checkout "
            "after they have explicitly agreed to pay. "
            "This creates a Razorpay TEST MODE order. "
            "It does not mean the payment has succeeded."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},
        ]

    # -------------------------------------------------
    # TOOL EXECUTION
    # -------------------------------------------------

    def execute_tool(
        self,
        name: str,
        arguments: dict,
    ):
        if name == "add_to_cart":

            if self.mutation_executed:
                return {
                    "success": False,
                    "action": "ADD_TO_CART",
                    "reason": (
                        "A cart mutation has already been "
                        "executed for this request."
                    ),
                }

            result = add_to_cart(
                db=self.db,
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,
                product_id=arguments["product_id"],
                quantity=arguments.get("quantity", 1),
            )

            if result.get("success"):
                self.mutation_executed = True

            return result
        if name == "prepare_checkout":

            service = CheckoutService(self.db)

            return service.prepare_checkout(
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,
            )
        
        if name == "resolve_product":

            return resolve_product(
                db=self.db,
                product_name=arguments["product_name"],
            )

        
        if name == "confirm_checkout":

            if self.checkout_executed:
                return {
                    "allowed": False,
                    "status": "CHECKOUT_ALREADY_CREATED",
                    "reason": (
                        "A Razorpay checkout order has already "
                        "been created for this request."
                    ),
                }

            service = CheckoutService(self.db)
            result = service.confirm_checkout(
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,       
            )

            if result.get("status") == "RAZORPAY_ORDER_CREATED":
                self.checkout_executed = True

            return result
        if name == "get_cart":

            return get_cart(
                db=self.db,
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,
            )

        if name == "get_order_status":
            service = OrderService(self.db)

            return service.get_order_status(
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,
                order_id=arguments.get("order_id"),
            )

        if name == "get_order_history":
            service = OrderService(self.db)

            return service.get_order_history(
                merchant_id=self.merchant_id,
                customer_id=self.customer_id,
                limit=arguments.get("limit", 10),
            )

        if name == "search_products":

            return search_products(
                db=self.db,
                query=arguments.get("query"),
                category=arguments.get("category"),
                max_price=arguments.get("max_price"),
                limit=10,
            )

        if name == "get_cross_sells":

            return get_cross_sells(
                db=self.db,
                product_id=arguments["product_id"],
            )

        if name == "get_upsells":

            return get_upsells(
                db=self.db,
                product_id=arguments["product_id"],
            )

        if name == "check_discount_policy":

            return check_discount_policy(
                db=self.db,
                merchant_id=self.merchant_id,
                discount_percent=arguments[
                    "discount_percent"
                ],
            )

        if name == "check_payment_policy":

            return check_payment_policy(
                db=self.db,
                merchant_id=self.merchant_id,
                amount=arguments["amount"],
            )

        raise ValueError(
            f"Unknown tool: {name}"
        )

    # -------------------------------------------------
    # MAIN AGENT
    # -------------------------------------------------

    def chat(
        self,
        user_message: str,
    ):
        self.mutation_executed = False
        self.checkout_executed = False
        payment_result = None
        messages = [
            {
                "role": "system",
                "content": """
You are TechNova's AI commerce assistant.

You help customers find products and make
relevant recommendations.

IMPORTANT TOOL RULES:

PRODUCTS:
- If the customer asks about a product, ALWAYS
  use search_products before answering.
- Never invent a product, price, stock level,
  specification, or availability.

CROSS-SELL:
- If the customer asks what accessories or products
  go well with a product, use get_cross_sells.

UPSELL:
- If the customer asks for a better or more
  expensive alternative, use get_upsells.

DISCOUNTS:
- If the customer asks for ANY discount, ALWAYS
  call check_discount_policy.
- Do NOT ask the customer for the purchase amount
  before checking the discount policy.

PAYMENTS:
- If the customer asks to pay, charge, purchase,
  checkout, or make a payment, ALWAYS call
  check_payment_policy.
- Never claim that a payment succeeded.
- Never execute a payment.

CART:
- Only use add_to_cart when the customer explicitly
  asks you to add a product.
- Never add a product merely because you recommended it.
- Never invent a product_id.
- A product number in a recommendation is NOT a
  database product_id.
- Use resolve_product when the customer gives a
  product name.
- The result returned by add_to_cart is authoritative.
- Never calculate prices or cart totals yourself.
- Prices are in INR. Always use ₹.
- If the customer asks what is in their cart,
  always use get_cart.
- Never ask the customer to provide product IDs
  or product names to inspect their own cart.
- The backend cart result is authoritative.
- Never calculate the cart total yourself.

CART DISPLAY:

- When showing cart contents to the customer,
  use the product_name returned by get_cart.
- Do not show database product IDs unless the
  customer specifically asks for them.
- Show prices in INR using ₹.
- Use the backend subtotal and total exactly as returned.
- Never calculate the total yourself.

CART MUTATION:
- add_to_cart changes database state.
- Call add_to_cart at most ONCE per user request.
- After add_to_cart succeeds, STOP using tools.
- Do not call add_to_cart again to verify the result.
- Do not add the same product twice unless the
  customer explicitly requests quantity greater than one.

PRODUCT ID SAFETY:
- Never assume "product 1" means database ID 1.
- If the customer says "add product 1" or "first one", they mean the FIRST search result you returned. 
- You MUST map "product 1", "product 2", etc., to the actual database product_id of the 1st, 2nd, etc. item in your previous search_products results.
- Never guess a database product ID.
- Only use IDs returned by search_products or
  resolve_product.
- If the referenced product cannot be determined,
  ask the customer to clarify.

ORDER STATUS:

- If the customer asks about their order status,
  payment status, or recent order, ALWAYS use
  get_order_status.

- Never invent an order status.

- Never claim an order is paid, confirmed,
  cancelled, or completed unless get_order_status
  returns that status.

- If the customer gives an order ID, pass that
  order ID to get_order_status.

- If the customer does not give an order ID,
  get_order_status should return their most recent order.

- Preserve the exact status values returned by
  get_order_status.

- Never replace CONFIRMED with COMPLETED.

- Never replace PAID with another payment status.

ORDER HISTORY:

- If the customer asks for previous orders,
  order history, past purchases, or recent orders,
  ALWAYS use get_order_history.

- The tool result is authoritative.

- You MUST include every order returned by
  get_order_history unless the customer explicitly
  asks for a smaller number.

- Never omit an order returned by the tool.

- Never invent an order.

- Never change an order ID.

- Never change an amount.

- Never change an order status.

- Never change a payment status.

- Preserve status values exactly as returned.

- "CONFIRMED" means CONFIRMED.
- "COMPLETED" means COMPLETED.
- "PAID" means PAID.

- Do not reinterpret CONFIRMED as COMPLETED.

- Do not reinterpret PAID as another status.

- If an order has no items, still include the order
  and do not invent products.

- If an order has items, report the items returned
  by the tool.

- Keep the response concise but complete.

- When get_order_history returns a "message" field,
  use that message as the factual order history.
- Do not rewrite, reinterpret, remove, or change
  any order in that message.

DATA ACCURACY:

- Tool results are authoritative database data.
- Do not summarize away important records.
- Do not silently omit records.
- Do not modify values returned by tools.

CHECKOUT:
- If the customer explicitly asks to checkout,
  use prepare_checkout.
- prepare_checkout does NOT make a payment.
- Never claim checkout succeeded unless the backend
  explicitly reports success.

CONFIRMATION:
- A customer must explicitly confirm before
  confirm_checkout can be used.
- Examples:
  "yes"
  "yes, proceed"
  "confirm"
  "go ahead and pay"
  "I confirm the payment"

PAYMENT STATUS:
- confirm_checkout does NOT mean payment succeeded.
- RAZORPAY_ORDER_CREATED means a Razorpay order
  was created, but payment has NOT necessarily happened.
- Never say "payment successful" for
  RAZORPAY_ORDER_CREATED.
- Never say "payment confirmed" for
  RAZORPAY_ORDER_CREATED.
- Never say "order is being processed" for
  RAZORPAY_ORDER_CREATED.
- Only say payment succeeded when the backend
  explicitly returns PAYMENT_SUCCESS.

SAFETY:
- Never bypass the Policy Engine.
- Never invent policy decisions.
- Never exceed merchant limits.

Keep responses concise, natural, and helpful.
""",
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        tools = self.get_tools()

        for _ in range(5):

            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools,
            )

            message = response["message"]

            # -----------------------------------------
            # Qwen has finished
            # -----------------------------------------
            if not message.get("tool_calls"):

                result = {
                    "response": message["content"],
                }

                if payment_result:
                    result["payment"] = payment_result["payment"]

                return result

            # Add Qwen's tool request
            messages.append(message)

            # -----------------------------------------
            # Execute tools
            # -----------------------------------------
            for tool_call in message["tool_calls"]:

                function = tool_call["function"]

                name = function["name"]

                arguments = function.get(
                    "arguments",
                    {},
                )

                # -------------------------------------
                # HARD CART MUTATION SAFETY
                # -------------------------------------
                if name == "add_to_cart":

                    if self.mutation_executed:

                        result = {
                            "success": False,
                            "action": "ADD_TO_CART",
                            "reason": (
                                "A cart mutation has already "
                                "been executed for this request."
                            ),
                        }

                    else:

                        result = self.execute_tool(
                            name,
                            arguments,
                        )

                        if result.get("success"):
                            self.mutation_executed = True

                    messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(
                                result,
                                default=str,
                            ),
                        }
                    )

                    # ---------------------------------
                    # IMPORTANT:
                    # Do NOT allow Qwen to call another
                    # mutation in this request.
                    # ---------------------------------
                    return self._finalize_tool_response(
                        messages,
                        payment_result,
                    )

                # -------------------------------------
                # CHECKOUT MUTATION
                # -------------------------------------
                if name == "confirm_checkout":

                    result = self.execute_tool(
                        name,
                        arguments,
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(
                                result,
                                default=str,
                            ),
                        }
                    )

                    if result.get("status") == "RAZORPAY_ORDER_CREATED":
                        payment_result = result

                        return {
                            "response": (
                                "Your checkout is ready. "
                                "A Razorpay test order has been "
                                "created. Payment has NOT been completed."
                            ),
                            "payment": result["payment"],
                        }

                    return {
                        "response": result.get(
                            "reason",
                            "Checkout could not be completed.",
                        )
                    }

                # -------------------------------------
                # Normal tools
                # -------------------------------------
                result = self.execute_tool(
                    name,
                    arguments,
                )

                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

        return {
            "response": (
                "I couldn't complete the request "
                "within the allowed steps."
            )
        }

    def _finalize_tool_response(
        self,
        messages,
        payment_result=None,
    ):
        response = ollama.chat(
            model=self.model,
            messages=messages,
        )

        result = {
            "response": response["message"]["content"],
        }

        if payment_result:
            result["payment"] = payment_result["payment"]

        return result