from sqlalchemy.orm import Session

from app.models import Product


def search_products(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    max_price: float | None = None,
    limit: int = 10,
):
    """
    Search the merchant catalog.
    """

    products_query = (
        db.query(Product)
        .filter(Product.active.is_(True))
    )

    if category:
        products_query = products_query.filter(
            Product.category == category
        )

    if max_price is not None:
        products_query = products_query.filter(
            Product.price <= max_price
        )

    if query:
        search_term = f"%{query}%"

        products_query = products_query.filter(
            Product.name.ilike(search_term)
        )

    products = (
        products_query
        .order_by(Product.price.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "price": float(product.price),  # type: ignore[arg-type]
            "inventory": product.inventory,
        }
        for product in products
    ]
def resolve_product(
    db: Session,
    product_name: str,
):
    """
    Resolve a natural-language product name
    to one real product from the catalog.
    """

    product = (
        db.query(Product)
        .filter(
            Product.active.is_(True),
            Product.name.ilike(product_name),
        )
        .first()
    )

    if not product:
        return {
            "found": False,
            "product": None,
        }

    return {
        "found": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "price": float(product.price),  # type: ignore[arg-type]
            "inventory": product.inventory,
        },
    }