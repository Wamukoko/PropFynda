import os
from pathlib import Path

# Set working directory to project root so sqlite:///./data/listings.db resolves correctly
BASE_DIR = Path(r"C:\Users\Eric\Desktop\QejaAPI\property-scraper-api")
os.chdir(BASE_DIR)

from app.database import SessionLocal
from app.scraper.runner import scrape_platform
from app.scraper.registry import load_platforms

db = SessionLocal()
try:
    import sqlite3
    conn = sqlite3.connect(str(BASE_DIR / "data" / "listings.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT platform_id FROM scrape_runs WHERE status='ok' OR status='error'")
    completed_platforms = {row[0] for row in cursor.fetchall()}
    conn.close()

    for platform in load_platforms():
        pid = platform["id"]
        if pid in completed_platforms:
            print(f"Skipping {pid} (already run/attempted)")
            continue
        if platform.get("active", True):
            print(f"Scraping {pid}...")
            try:
                r = scrape_platform(db, pid)
                print(f"  Result: {r['status']} - Saved: {r['listings_saved']} - Found: {r['listings_found']}")
            except Exception as e:
                print(f"  Failed with exception: {e}")
finally:
    db.close()