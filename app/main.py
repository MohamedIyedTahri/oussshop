from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import Base, engine, get_db
from app.schemas import WebhookRequest, WebhookResponse, ProductRecommendation, FeedRefreshResponse
from app.parser import fetch_and_parse_feed
from app.search import search_products
from app.llm import detect_intent_and_extract, generate_response
from app.models import ChatLog

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tunisian E-commerce Chatbot API",
    description="FastAPI chatbot backend that parses RSS Google Merchant feed and answers queries in Derja",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/webhook/whatsapp", response_model=WebhookResponse)
async def webhook_whatsapp(payload: WebhookRequest, db: Session = Depends(get_db)):
    """
    Receives user messages, identifies intent, searches the product catalog,
    and returns a friendly response in Tunisian Derja along with structured product recommendations.
    """
    user_id = payload.user_id
    message = payload.message
    logger.info(f"Received webhook message from user={user_id}: '{message}'")
    
    # Step 1: Detect intent and extract keywords/price constraints using LLM
    try:
        extraction = await detect_intent_and_extract(message)
        intent = extraction.get("intent", "smalltalk")
        keywords = extraction.get("keywords", "")
        price_limit = extraction.get("price_limit")
        logger.info(f"Intent classified: {intent} | Keywords: '{keywords}' | Price limit: {price_limit}")
    except Exception as e:
        logger.error(f"Failed to detect intent/extract parameters: {e}")
        intent = "product_search"
        keywords = message
        price_limit = None
        
    # Step 2: Search catalog if intent relates to products
    products = []
    if intent in ["product_search", "price_inquiry", "recommendation"]:
        try:
            products = search_products(db, keywords=keywords, price_limit=price_limit, limit=3)
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            products = []
            
    # Step 3: Generate the chat reply in Derja
    try:
        reply = await generate_response(message, intent, products)
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        reply = "Aslema! Fama mochkla fil system. Najem n3awnek fi 7aja okhra?"

    # Step 4: Log the conversation in Postgres
    try:
        chat_entry = ChatLog(
            user_id=user_id,
            message=message,
            intent=intent,
            reply=reply
        )
        db.add(chat_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save chat log: {e}")
        # Rollback in case of database transaction error
        db.rollback()

    # Step 5: Format recommendations for output response
    recommended_products = []
    for p in products:
        recommended_products.append(
            ProductRecommendation(
                title=p.title,
                price=f"{p.price} TND" if p.price else (p.price_str or "Non spécifié"),
                url=p.link or "",
                image=p.image_link or ""
            )
        )
        
    return WebhookResponse(
        reply=reply,
        products=recommended_products
    )

def bg_refresh_feed(feed_url: str = None):
    # Setup new DB session for background task
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        fetch_and_parse_feed(db, feed_url)
    except Exception as e:
        logger.error(f"Background XML feed parsing failed: {e}")
    finally:
        db.close()

@app.post("/admin/refresh", response_model=FeedRefreshResponse)
def refresh_catalog(
    background_tasks: BackgroundTasks,
    sync: bool = False,
    feed_url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to refresh the product catalog.
    Can be run synchronously or as a background task.
    """
    if sync:
        try:
            count = fetch_and_parse_feed(db, feed_url)
            return FeedRefreshResponse(
                status="success",
                processed_count=count,
                message=f"Successfully imported {count} products synchronously."
            )
        except Exception as e:
            logger.error(f"Synchronous feed sync failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Feed sync failed: {str(e)}"
            )
    else:
        background_tasks.add_task(bg_refresh_feed, feed_url)
        return FeedRefreshResponse(
            status="accepted",
            processed_count=0,
            message="Product feed refresh started in the background."
        )
