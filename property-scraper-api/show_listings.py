import os, sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'data', 'listings.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT id, platform_name, title, price_amount, price_currency, source_url FROM listings ORDER BY first_seen_at DESC LIMIT 10')
for row in cur.fetchall():
    print(row)
conn.close()
