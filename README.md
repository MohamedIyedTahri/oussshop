# 🚀 Tunisian E-commerce Chatbot Backend

This is a production-ready, lightweight AI-driven chatbot backend for Tunisian e-commerce stores. It integrates with WhatsApp / Facebook Messenger webhooks, reads standard Google Merchant XML product feeds, stores products in PostgreSQL, and generates friendly natural responses in the Tunisian dialect (**Derja**) using the OpenRouter LLM API.

---

## 🎯 Features

1. **Automatic Feed Ingestion**: Ingests product feeds in Google Merchant RSS XML format, parses prices, and stores them in PostgreSQL.
2. **Derja Intent Classification**: Uses LLM to determine customer intent (search, price inquiry, recommendation, FAQ, or smalltalk) and extract search query parameters (keywords, price limit) from Derja.
3. **Optimized Local Catalog Search**: Performs fast keyword searches on the PostgreSQL DB, filters by price limit, and checks stock availability.
4. **Natural Derja Responses**: Generates friendly responses via OpenRouter, including direct product links and pricing in TND.
5. **Stateful Logs**: Saves all conversation history (messages, responses, intents) in Postgres for analytics and audit.
6. **Dockerized Deployment**: Fully containerized using Docker and Docker Compose.

---

## 📁 Project Structure

```
oussshop/
├── app/
│   ├── __init__.py
│   ├── config.py         # Configs (env variables, DB, OpenRouter)
│   ├── database.py       # SQLAlchemy engine, session maker, and DB base
│   ├── models.py         # SQLAlchemy models (Product, ChatLog)
│   ├── schemas.py        # Pydantic schemas for API inputs & outputs
│   ├── parser.py         # XML RSS parser & background sync worker
│   ├── search.py         # Database search logic (ILIKE + price limit)
│   ├── llm.py            # OpenRouter API client (intent classification + reply)
│   └── main.py           # FastAPI endpoints (webhook, health, admin sync)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── test_local.py         # End-to-end local validation script
└── README.md
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:
```env
PORT=8000
FEED_URL=https://equip-home.tn/api/meta/meta-feed.xml
DATABASE_URL=postgresql://postgres:postgres@db:5432/chatbot_db
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free
```

---

## 🚀 Running the System

### Prerequisites
- Docker & Docker Compose installed.
- A valid OpenRouter API Key.

### 1. Build and Start Containers
Run the following command to start PostgreSQL and the FastAPI server:
```bash
docker compose up --build -d
```

### 2. Verify Services are Running
- **FastAPI Documentation (Swagger UI)**: http://localhost:8000/docs
- **Health Check Endpoint**: http://localhost:8000/health

### 3. Sync the Catalog
To manually trigger the ingestion of the product feed, send a POST request to the admin endpoint:
```bash
curl -X POST http://localhost:8000/admin/refresh?sync=true
```
*(This will download products from the `FEED_URL`, parse prices, and populate the PostgreSQL database. Subsequent requests can run in the background by setting `sync=false`).*

---

## 💬 API Webhook Specification

### `POST /webhook/whatsapp`

Used to interface directly with Meta WhatsApp Cloud API / Facebook Messenger webhooks.

#### **Request Payload**
```json
{
  "user_id": "user_whatsapp_phone_number_or_messenger_id",
  "message": "fama 3andkomch ventilateur a9al mel 100dt?"
}
```

#### **Response Payload**
```json
{
  "reply": "Aslema! Ey n3am fama, 3andna 'Ventilateur STAR ONE' b 45.90 TND akahaw. Tnajem tchoufo men hna: https://equip-home.tn/products/40",
  "products": [
    {
      "title": "Ventilateur STAR ONE",
      "price": "45.90 TND",
      "url": "https://equip-home.tn/products/40",
      "image": "https://equip-home.tn/api/file/f/Avfile/40"
    }
  ]
}
```

---

## 🧪 Local Testing

You can run the full test suite locally (without docker/postgres) using an in-memory SQLite database:

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the tests:
   ```bash
   python3 test_local.py
   ```
