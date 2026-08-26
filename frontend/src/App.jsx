import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm TechNova's AI shopping assistant. What are you looking for today?",
    },
  ]);

  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(false);

  const customerId = 1;

  async function sendMessage() {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || loading) {
      return;
    }

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: trimmedMessage,
      },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/agent/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            customer_id: customerId,
            message: trimmedMessage,
          }),
        }
      );

      const data = await response.json();

      if (
        data.payment &&
        data.payment.status === "RAZORPAY_ORDER_CREATED"
      ) {
        setPayment(data.payment);
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
          `Backend returned ${response.status}`
        );
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.response,
        },
      ]);

    } catch (error) {
      console.error("Agent error:", error);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: `Backend error: ${error.message}`,
        },
      ]);

    } finally {
      // VERY IMPORTANT:
      // The request is finished.
      // Remove the Thinking indicator.
      setLoading(false);
    }
  }
  function openRazorpayCheckout() {
    if (!payment) {
      return;
    }

    const options = {
      key: payment.key_id,

      amount: payment.amount,

      currency: payment.currency,

      name: "TechNova",

      description: "TechNova AI Commerce Order",

      order_id: payment.order_id,

      handler: async function (response) {
        console.log(
          "Razorpay payment response:",
          response
        );

        try {
          const verifyResponse = await fetch(
            `${API_URL}/payment/verify`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                customer_id: customerId,

                razorpay_order_id:
                  response.razorpay_order_id,

                razorpay_payment_id:
                  response.razorpay_payment_id,

                razorpay_signature:
                  response.razorpay_signature,
              }),
            }
          );

          const result = await verifyResponse.json();

          if (!verifyResponse.ok) {
            throw new Error(
              result.detail ||
              "Payment verification failed."
            );
          }

          setMessages((previous) => [
            ...previous,
            {
              role: "assistant",
              content:
                "Payment verified successfully. Your Razorpay test payment has been confirmed.",
            },
          ]);

          setPayment(null);

        } catch (error) {
          console.error(
            "Payment verification error:",
            error
          );

          setMessages((previous) => [
            ...previous,
            {
              role: "assistant",
              content:
                "The payment was received by Razorpay, but our server could not verify it.",
            },
          ]);
        }
      },

      modal: {
        ondismiss: function () {
          console.log(
            "Razorpay checkout closed."
          );
        },
      },

      theme: {
        color: "#3157d5",
      },
    };

    const razorpay = new window.Razorpay(options);

    razorpay.open();
  }
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>TechNova</h1>
          <p>AI Commerce Assistant</p>
        </div>

        <div className="customer-badge">
          Customer #{customerId}
        </div>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.map((item, index) => (
            <div
              key={index}
              className={`message-row ${item.role}`}
            >
              <div className="message">
                {item.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message">
                Thinking...
              </div>
            </div>
          )}
        </div>
        {payment && (
          <div className="payment-card">
            <div>
              <strong>Checkout ready</strong>

              <p>
                Your Razorpay checkout is ready.
              </p>
            </div>

            <button
              className="pay-button"
              onClick={openRazorpayCheckout}
            >
              Pay ₹{(payment.amount / 100).toLocaleString("en-IN")}
            </button>
          </div>
        )}
        <div className="input-area">
          <textarea
            value={message}
            onChange={(event) =>
              setMessage(event.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Ask me about laptops, phones, accessories..."
            rows={2}
            disabled={loading}
          />

          <button
            onClick={sendMessage}
            disabled={
              loading || !message.trim()
            }
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </main>
    </div>
  );
}

export default App;