from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditService:

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        merchant_id: int,
        action: str,
        reason: str,
        status: str,
        customer_id: int | None = None,
        metadata: dict | None = None,
    ):
        event = AuditEvent(
            merchant_id=merchant_id,
            customer_id=customer_id,
            action=action,
            reason=reason,
            status=status,
            event_metadata=metadata,
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event