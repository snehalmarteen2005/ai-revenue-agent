from sqlalchemy.orm import Session

from app.recommendations.engine import RevenueEngine


def get_cross_sells(
    db: Session,
    product_id: int,
):
    engine = RevenueEngine(db)

    return engine.get_cross_sell_candidates(
        product_id=product_id,
        limit=5,
    )


def get_upsells(
    db: Session,
    product_id: int,
):
    engine = RevenueEngine(db)

    return engine.get_upsell_candidates(
        product_id=product_id,
        limit=5,
    )