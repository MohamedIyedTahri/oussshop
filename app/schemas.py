from pydantic import BaseModel, Field
from typing import List, Optional

class WebhookRequest(BaseModel):
    user_id: str = Field(..., description="The unique user identifier from WhatsApp or Messenger")
    message: str = Field(..., description="The user's text message")

class ProductRecommendation(BaseModel):
    title: str = Field(..., description="Product title")
    price: str = Field(..., description="Product price with currency, e.g., '89.90 TND'")
    url: str = Field(..., description="URL to view/buy the product")
    image: str = Field(..., description="Image link of the product")

class WebhookResponse(BaseModel):
    reply: str = Field(..., description="Friendly response generated in Tunisian Derja")
    products: List[ProductRecommendation] = Field(default=[], description="List of recommended products matching the query")

class FeedRefreshResponse(BaseModel):
    status: str
    processed_count: int
    message: str
