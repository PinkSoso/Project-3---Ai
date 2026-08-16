import csv
import os
import random
import sys
from datetime import datetime, timedelta

from faker import Faker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.db.session import SessionLocal, engine
from backend.models.db_models import Base, Product, Subscriber

fake = Faker()

SEGMENTS = ["Lapsed_90d", "New_signups", "High_Value", "Browse_only"]
SUBSCRIBERS_PER_SEGMENT = 100

BROWSE_PRODUCTS = [
    "Lumino Glow AHA Concentrate",
    "Lumino Soft Day Cream",
    "Lumino Shield SPF 50 Daily Fluid",
    "Lumino Balance Niacinamide Serum",
    "Lumino Firm Peptide Booster",
    "Lumino Restore Night Cream",
    "Lumino Renew Retinol Drops",
]


def generate_subscribers(db):
    today = datetime.utcnow()

    for segment in SEGMENTS:
        for _ in range(SUBSCRIBERS_PER_SEGMENT):
            sub = Subscriber()
            sub.email = fake.email()
            sub.first_name = fake.first_name()
            sub.segment = segment

            if segment == "Lapsed_90d":
                sub.last_purchase_date = today - timedelta(days=random.randint(91, 400))
                sub.total_spend = round(random.uniform(20, 150), 2)
                sub.browse_product = None
                sub.created_at = today - timedelta(days=random.randint(180, 730))

            elif segment == "New_signups":
                sub.last_purchase_date = None
                sub.total_spend = 0.0
                sub.browse_product = None
                sub.created_at = today - timedelta(days=random.randint(1, 13))

            elif segment == "High_Value":
                sub.last_purchase_date = today - timedelta(days=random.randint(1, 45))
                sub.total_spend = round(random.uniform(201, 900), 2)
                sub.browse_product = None
                sub.created_at = today - timedelta(days=random.randint(90, 730))

            elif segment == "Browse_only":
                sub.last_purchase_date = None
                sub.total_spend = 0.0
                sub.browse_product = random.choice(BROWSE_PRODUCTS)
                sub.created_at = today - timedelta(days=random.randint(1, 60))

            db.add(sub)

    db.commit()
    print(f"  Seeded {SUBSCRIBERS_PER_SEGMENT * len(SEGMENTS)} subscribers.")


def seed_products(db):
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "products_dataset.csv")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product = Product(
                name=row["name"],
                sub_category=row["sub_category"],
                price=float(row["price"]),
                description=row["description"],
                copy_hook=row["copy_hook"],
                is_active=row["is_active"].strip().lower() == "true",
                created_at=datetime.fromisoformat(row["created_at"].replace("+00:00", "")),
            )
            db.merge(product)

    db.commit()
    print("  Seeded products from products_dataset.csv.")


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(Subscriber).first()
    if existing:
        print("Database already initialised — skipping seed.")
        db.close()
        return

    print("Initialising database...")
    generate_subscribers(db)
    seed_products(db)
    print("Database ready.")
    db.close()


if __name__ == "__main__":
    init_db()
