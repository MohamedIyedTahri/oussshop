import unittest
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import decimal

# Import project modules
from app.database import Base
from app.models import Product
from app.parser import fetch_and_parse_feed, parse_price
from app.search import search_products

class TestEcomChatbot(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_price_parsing(self):
        self.assertEqual(parse_price("209.90 TND"), decimal.Decimal("209.90"))
        self.assertEqual(parse_price("45,90 TND"), decimal.Decimal("45.90"))
        self.assertEqual(parse_price("1 200.50 DT"), decimal.Decimal("1200.50"))
        self.assertEqual(parse_price("89"), decimal.Decimal("89"))
        self.assertIsNone(parse_price(None))

    def test_xml_feed_parsing_and_upsert(self):
        # We can parse the actual live XML feed to test real ingestion
        # (This tests connection and structure parsing)
        try:
            count = fetch_and_parse_feed(self.db)
            print(f"\n[Test] Parsed and saved {count} products from live XML feed.")
            self.assertGreater(count, 0, "No products were parsed from the live XML feed.")
            
            # Check if products were added to DB
            products = self.db.query(Product).all()
            self.assertEqual(len(products), count)
            
            # Validate field mapping on one product
            sample = products[0]
            self.assertIsNotNone(sample.id)
            self.assertIsNotNone(sample.title)
            self.assertIsNotNone(sample.price)
            self.assertIsNotNone(sample.link)
            self.assertTrue(sample.link.startswith("http"))
            print(f"[Test] Sample product loaded: ID={sample.id}, Title='{sample.title}', Price={sample.price} TND")
        except Exception as e:
            self.fail(f"Failed to fetch or parse live XML feed: {e}")

    def test_product_searching(self):
        # Add test products
        p1 = Product(
            id="101",
            title="Ventilateur STAR ONE",
            description="Ventilateur de table de qualité",
            availability="in stock",
            price=decimal.Decimal("45.90"),
            link="https://example.com/p1"
        )
        p2 = Product(
            id="102",
            title="Aspirateur sans sac",
            description="Aspirateur puissant 2000W",
            availability="in stock",
            price=decimal.Decimal("189.90"),
            link="https://example.com/p2"
        )
        p3 = Product(
            id="103",
            title="Aspirateur robot",
            description="Aspirateur intelligent autonome",
            availability="out of stock",
            price=decimal.Decimal("350.00"),
            link="https://example.com/p3"
        )
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        # Test search by keyword
        results = search_products(self.db, keywords="aspirateur")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "102")  # p3 is out of stock, so only p2 is returned

        # Test search with price limit
        results_budget = search_products(self.db, keywords="aspirateur", price_limit=100.0)
        self.assertEqual(len(results_budget), 0)  # p2 is 189.90, so it should be filtered out

        # Test ventilateur search
        results_vent = search_products(self.db, keywords="ventilateur", price_limit=50.0)
        self.assertEqual(len(results_vent), 1)
        self.assertEqual(results_vent[0].id, "101")

if __name__ == "__main__":
    unittest.main()
