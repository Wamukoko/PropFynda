from app.database import SessionLocal
from app.scraper.runner import scrape_all_active_platforms

db = SessionLocal()
try:
    results = scrape_all_active_platforms(db)
    for r in results:
        print(f'{r["platform_id"]}: {r["status"]} - {r["listings_saved"]} listings saved')
finally:
    db.close()