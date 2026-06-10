import xml.etree.ElementTree as ET
import requests
from sqlalchemy.orm import Session
from app.models import Product
from app.config import settings
import re
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google merchant feed namespace
NS = {'g': 'http://base.google.com/ns/1.0'}

def parse_price(price_str: str) -> Decimal:
    """
    Parses a price string like '209.90 TND' or '89.90' into a Decimal.
    Returns None if parsing fails.
    """
    if not price_str:
        return None
    # Remove letters (like TND, DT) and whitespace
    clean_str = re.sub(r'[a-zA-Z\s]', '', price_str)
    
    # Handle commas and dots
    if ',' in clean_str and '.' in clean_str:
        clean_str = clean_str.replace(',', '')
    elif ',' in clean_str:
        # Check if comma is decimal separator (e.g. 89,90)
        parts = clean_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            clean_str = clean_str.replace(',', '.')
        else:
            clean_str = clean_str.replace(',', '')
    try:
        return Decimal(clean_str)
    except Exception as e:
        logger.error(f"Error parsing price '{price_str}': {e}")
        return None

def fetch_and_parse_feed(db: Session, feed_url: str = None) -> int:
    """
    Fetches the XML feed, parses products, and performs an upsert in the database.
    Returns the number of products processed.
    """
    url = feed_url or settings.FEED_URL
    logger.info(f"Fetching XML feed from {url}...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    logger.info("Feed fetched successfully. Parsing XML...")
    root = ET.fromstring(response.content)
    
    items = root.findall('.//item')
    logger.info(f"Found {len(items)} items in feed. Upserting into DB...")
    count = 0
    
    for item in items:
        def get_tag_value(tag_name: str) -> str:
            # Try namespaced tag first
            el = item.find(f'g:{tag_name}', NS)
            if el is not None:
                return el.text
            # Try tag without namespace
            el = item.find(tag_name)
            if el is not None:
                return el.text
            return None
        
        prod_id = get_tag_value('id')
        if not prod_id:
            logger.warning("Found item without a product ID. Skipping.")
            continue
            
        title = get_tag_value('title')
        description = get_tag_value('description')
        condition = get_tag_value('condition')
        availability = get_tag_value('availability')
        brand = get_tag_value('brand')
        price_str = get_tag_value('price')
        link = get_tag_value('link')
        image_link = get_tag_value('image_link')
        
        category = get_tag_value('product_type') or get_tag_value('google_product_category')
        
        # Clean CDATA markers if present in standard fields (elementtree usually strips them automatically, but good to ensure)
        if title:
            title = title.strip()
        if description:
            description = description.strip()
            
        parsed_price = parse_price(price_str)
        
        # Find or create product
        db_product = db.query(Product).filter(Product.id == prod_id).first()
        if db_product:
            db_product.title = title or db_product.title
            db_product.description = description or db_product.description
            db_product.condition = condition or db_product.condition
            db_product.availability = availability or db_product.availability
            db_product.brand = brand or db_product.brand
            db_product.price_str = price_str or db_product.price_str
            db_product.price = parsed_price if parsed_price is not None else db_product.price
            db_product.link = link or db_product.link
            db_product.image_link = image_link or db_product.image_link
            db_product.category = category or db_product.category
        else:
            new_prod = Product(
                id=prod_id,
                title=title or "Unknown Product",
                description=description,
                condition=condition,
                availability=availability,
                brand=brand,
                price_str=price_str,
                price=parsed_price,
                link=link,
                image_link=image_link,
                category=category
            )
            db.add(new_prod)
            
        count += 1
        
    db.commit()
    logger.info(f"Database upsert complete. Total processed: {count} products.")
    return count
