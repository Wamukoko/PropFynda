import sys, os
sys.path.append('c:/Users/Eric/Desktop/QejaAPI/property-scraper-api')
from app.scraper.runner import scrape_platform
from app.database import SessionLocal

db = SessionLocal()
result = scrape_platform(db, 'propertyke')
print('Scrape result:', result)
