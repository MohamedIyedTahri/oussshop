from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models import Product
from typing import List, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def search_products(
    db: Session,
    keywords: Optional[str] = None,
    price_limit: Optional[float] = None,
    limit: int = 5
) -> List[Product]:
    """
    Search database for products matching keywords and price limit.
    Only recommends items that are in stock.
    """
    query = db.query(Product)
    
    # Filter for in-stock products
    query = query.filter(
        or_(
            Product.availability.ilike("in stock"),
            Product.availability.ilike("in_stock"),
            Product.availability.is_(None)
        )
    )
    
    # Apply keyword filter (AND of all word conditions)
    if keywords:
        words = [w.strip() for w in keywords.split() if w.strip()]
        if words:
            conditions = []
            for word in words:
                conditions.append(
                    or_(
                        Product.title.ilike(f"%{word}%"),
                        Product.description.ilike(f"%{word}%"),
                        Product.category.ilike(f"%{word}%")
                    )
                )
            query = query.filter(and_(*conditions))
            
    # Apply price limit filter
    if price_limit is not None and price_limit > 0:
        query = query.filter(Product.price <= Decimal(str(price_limit)))
        
    # Get top items
    results = query.limit(limit).all()
    logger.info(f"Search query [keywords={keywords}, price_limit={price_limit}] returned {len(results)} results")
    return results
