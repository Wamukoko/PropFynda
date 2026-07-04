import sys, os
sys.path.append('c:/Users/Eric/Desktop/QejaAPI/property-scraper-api')
from app.database import SessionLocal
from app import models

db = SessionLocal()
rows = db.query(models.Listing).filter(models.Listing.platform_id=='propertyke').all()
print('PropertyKE count:', len(rows))
for r in rows[:20]:
    print(r.id, r.title, r.price_amount, r.source_url)
