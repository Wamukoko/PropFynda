import sqlite3
conn = sqlite3.connect(r'C:\Users\Eric\Desktop\QejaAPI\property-scraper-api\data\listings.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM listings")
total_listings = cursor.fetchone()[0]

cursor.execute("SELECT platform_id, COUNT(*) FROM listings GROUP BY platform_id")
by_platform = cursor.fetchall()

cursor.execute("SELECT platform_id, status, error FROM scrape_runs ORDER BY started_at DESC LIMIT 20")
runs = cursor.fetchall()

print(f"Total listings: {total_listings}")
print("Listings by platform:")
for p, count in by_platform:
    print(f"  {p}: {count}")

print("\nRecent scrape runs:")
for platform, status, error in runs:
    print(f"  {platform}: {status} - Error: {error}")

conn.close()