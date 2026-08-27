# AI Revenue Agent

This is an AI-powered commerce assistant designed specifically for **Track 01: AI Growth & Agentic Commerce**. It integrates an autonomous conversational agent with a robust backend architecture to facilitate product discovery, cart management, and secure checkout, all while ensuring that every financial action is strictly evaluated, governed by merchant policies, and thoroughly audited before processing via Razorpay.

## What We Built

- **Conversational Product Discovery:** Natural language search leveraging a local LLM to interact with a real product catalog.
- **Product Recommendations:** Cross-selling and upselling capabilities natively integrated as AI tools.
- **Natural-Language Cart Operations:** The AI can securely add items to the user's cart without hallucinating product IDs.
- **Checkout:** Streamlined checkout preparation via the AI.
- **Payment Policy Gating:** Strict backend evaluation of transaction limits and discounts.
- **Razorpay Test-Mode Payments:** Integrated payment gateway for testing secure end-to-end transactions.
- **Payment Verification:** Cryptographic signature verification for successful payments.
- **Razorpay Webhooks:** Idempotent webhook handling for asynchronous payment and order events.
- **Internal Orders:** Secure creation of database orders (`Order` and `OrderItem`) only after policy approval.
- **Inventory Updates:** Safe, transactional inventory decrements upon verified payment.
- **Order History:** Users can naturally query their past orders and payment statuses.
- **Audit Trail:** Comprehensive, immutable logging of all policy decisions and money actions.
- **Idempotent Handling:** Protection against duplicate webhooks and double-processing of payments.

## Why This Fits Track 01

This project directly addresses the track requirement: *"Every money action explainable, bounded and gated."*

- **Explainable:** Every transaction attempt generates an `AuditEvent` record detailing the action, the decision (ALLOWED/BLOCKED), a human-readable reason, and the mathematical metadata at the time of the event.
- **Bounded:** The `MerchantPolicy` database model bounds the AI by enforcing strict hard limits, such as `max_payment_amount` and `max_discount_percent`.
- **Gated:** The `CheckoutService` and `PolicyEngine` act as rigid gates. A Razorpay order is strictly blocked from being generated unless the policy engine explicitly approves the transaction. 
- **Transactable by an AI Buyer:** The AI acts on behalf of the user to discover items, manipulate the cart, and initiate checkout, completing a full commerce loop ending in a Razorpay Test Mode transaction.

## End-to-End Flow

```text
User
  ↓
AI Agent (Ollama Local)
  ↓
Product Search / Recommendations
  ↓
Cart Operations
  ↓
CheckoutService
  ↓
PolicyEngine (Evaluates Merchant limits)
  ↓
[ ALLOWED or BLOCKED ]
  ↓ (If Allowed)
Razorpay (Test Mode Order Creation)
  ↓
Payment Verification + Webhook
  ↓
Internal Order marked PAID
  ↓
OrderItems generated
  ↓
Inventory Update
  ↓
Order History updated
```
*Note: All money actions are rigidly enforced by the backend Python services, ensuring the system never blindly trusts the AI's intent.*

## Explainable, Bounded and Gated

### Explainable
The `AuditService` ensures complete explainability. Whenever a policy is checked (e.g., during checkout), an `AuditEvent` is generated. It records the exact reason a transaction was allowed or blocked, along with the numerical boundaries that were applied. 

### Bounded
The system's behavior is bounded by the `MerchantPolicy` database model. For example, if a merchant configures a `max_payment_amount` of ₹50,000, any cart total exceeding this value is structurally prohibited from reaching the payment gateway, regardless of the AI's instructions.

### Gated
Checkout is gated by the `CheckoutService`. When the AI invokes the `confirm_checkout` tool, the service synchronously evaluates the cart total against the `PolicyEngine`. If the policy fails, the service returns a `BLOCKED` status to the AI, and no Razorpay order is created.

## Audit Trail

The audit records are stored persistently in PostgreSQL in the `audit_events` table. A developer or administrator can easily inspect these records to trace exactly why a transaction succeeded or failed.

To view the most recent audit events, you can run the following query against the PostgreSQL database:

```sql
SELECT action, status, reason, event_metadata, created_at 
FROM audit_events 
ORDER BY created_at DESC 
LIMIT 5;
```

## Graceful Failure Demonstration

The application supports robust, graceful failures. 

**Scenario: User cart exceeds allowed payment amount**
1. The user builds a cart whose total exceeds the merchant's `max_payment_amount` policy.
2. The user asks the AI to check out.
3. The AI attempts to prepare/confirm the checkout, routing the request to the `CheckoutService`.
4. The `PolicyEngine` evaluates the amount and returns a `BLOCKED` status.
5. A detailed `AuditEvent` is recorded in the database explaining the limit breach.
6. **No Razorpay order is created.**
7. The AI gracefully receives the blocked response and translates it into a polite, human-readable apology to the user, explaining the store's transaction limits.

## Payment Flow

1. **Cart Preparation:** The user adds products to their cart via the AI.
2. **Policy Evaluation:** The checkout policy is evaluated against the cart's total.
3. **Razorpay Order:** A Razorpay Test Mode order is created **only** after Policy approval.
4. **Payment Completion:** The user completes the payment via the frontend.
5. **Verification (`/payment/verify`):** The backend verifies the Razorpay payment cryptographic signature.
6. **Webhook (`/payment/webhook`):** The backend asynchronously verifies the Razorpay webhook signature for events like `payment.captured`.
7. **Internal Order:** The internal database order is marked as paid and confirmed.
8. **OrderItems:** Individual `OrderItem` records are created from the cart.
9. **Inventory Update:** Product inventory is safely reduced.
10. **Idempotency:** The webhook logic ensures duplicate events do not result in double-deductions of inventory or redundant orders.

## Local Architecture

- **Frontend:** React/Vite 
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (with pgvector)
- **AI:** Ollama (running strictly locally, NO cloud AI dependency)
- **Payments:** Razorpay Test Mode

## Tech Stack

- Python 3
- FastAPI
- SQLAlchemy & Psycopg2
- React & Vite
- Node.js
- Ollama
- Razorpay Python SDK
- Docker & Docker Compose

## Project Structure

```text
C:\projects\ai-revenue-agent
├── backend/
│   ├── app/
│   │   ├── agent.py
│   │   ├── audit/
│   │   ├── cart/
│   │   ├── checkout/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── order/
│   │   ├── payments/
│   │   ├── policies/
│   │   ├── recommendations/
│   │   ├── seed.py
│   │   ├── seed_policy.py
│   │   └── tools/
│   ├── requirements.txt
│   ├── test_webhook.py
│   └── .env (Local only, not committed)
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── evaluation/
└── README.md
```

## Setup

These instructions will guide you through setting up the project locally for demonstration.

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd ai-revenue-agent
```

**2. PostgreSQL / Docker Setup**
Ensure Docker is installed and running.
```bash
docker-compose up -d postgres
```

**3. Backend Environment Setup**
```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**4. Required Environment Variables**
Create a `.env` file in the `backend/` directory. **Never commit this file.**
```env
# backend/.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/airevenue
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

**5. Ollama Setup**
Install [Ollama](https://ollama.com/) locally and pull the required model:
```bash
ollama run qwen2.5:3b
```

**6. Backend Startup**
```bash
# Inside the backend directory
uvicorn app.main:app --reload
```

**7. Frontend Startup**
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

**8. Webhook Testing**
To simulate a Razorpay webhook locally without exposing a public endpoint:
```bash
# Inside the backend directory
python test_webhook.py
```

## Environment Variables

The application relies on the following environment variables (set in `backend/.env`):

- `DATABASE_URL`: Connection string for PostgreSQL.
- `RAZORPAY_KEY_ID`: Your Razorpay Test Mode Key ID.
- `RAZORPAY_KEY_SECRET`: Your Razorpay Test Mode Key Secret.
- `RAZORPAY_WEBHOOK_SECRET`: The secret used to cryptographically verify Razorpay webhooks.

**WARNING:** The `.env` file contains sensitive credentials and is included in `.gitignore`. It must never be committed to version control.

## Demo Flow

For a 5-minute Track 01 pitch, we recommend following this flow:

1. **Product Discovery:** Ask the AI to find a product (e.g., "Show me laptops").
2. **Selection:** Select a product naturally from the chat.
3. **Cart Operation:** Tell the AI to add the item to the cart.
4. **Policy Check:** Ask the AI to proceed to checkout to trigger the `PolicyEngine` evaluation.
5. **Checkout:** Complete the transaction using the Razorpay Test Mode UI.
6. **Verification:** Show the terminal output confirming the webhook/payment verification.
7. **Order Creation:** Show the resulting `Order` and `OrderItem` rows in the database.
8. **Inventory Management:** Demonstrate that the product's inventory was reduced by the correct amount.
9. **Audit Trail:** Query the `audit_events` table to show the cryptographic/mathematical footprint of the transaction decision.
10. **Graceful Failure:** Attempt to buy an absurdly large quantity of items to trigger a `BLOCKED` policy response, demonstrating a graceful failure.

## Safety / Security Notes

- **Secret Management:** Razorpay API keys and database credentials are strictly managed via environment variables.
- **Verification:** Both frontend payment signatures and backend asynchronous webhooks are cryptographically verified.
- **Idempotency:** Duplicate payment processing is heavily guarded against to prevent double-charging or double-inventory deduction.
- **Environment Safety:** The `.env` file is excluded via `.gitignore`.
- **Database Safety:** PostgreSQL is run locally via Docker and is not exposed to the public internet.
- **Test Mode:** This repository relies exclusively on Razorpay Test Mode. No real funds are moved.

## Evaluation / Demo Evidence

Evaluators should pay special attention to:
- The fluidity of the AI-driven commerce interaction.
- The robust, backend-enforced payment policies.
- The mathematically sound auditability in the `audit_events` table.
- The secure integration with Razorpay (verification and webhooks).
- The transactionally safe inventory reductions.
- The system's ability to gracefully block and recover from a policy violation without crashing.

## Future Work

- **Production Deployment:** Migrating from a local Ollama instance to a scalable cloud LLM and deploying the backend to a PaaS.
- **Enhanced Observability:** Building an admin dashboard to visualize the `audit_events` table in real-time.
- **Advanced Revenue Optimization:** Implementing more dynamic discounting algorithms within the `PolicyEngine`.
