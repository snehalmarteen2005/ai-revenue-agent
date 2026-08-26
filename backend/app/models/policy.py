from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    max_discount_percent: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    max_ai_cart_items: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )

    payment_requires_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    max_payment_amount: Mapped[int] = mapped_column(
        Integer,
        default=100000,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )