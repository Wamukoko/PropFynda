import csv, os, sys
sys.path.append('c:/Users/Eric/Desktop/QejaAPI/property-scraper-api')
from app.database import SessionLocal
from app import models

def export(csv_path):
    db = SessionLocal()
    try:
        rows = db.query(models.Listing).all()
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['id','platform_id','platform_name','source_url','title','price_amount','price_currency','location_text','bedrooms','bathrooms','size_value','size_unit','agent_name','agency_name','agency_url','date_posted']
            writer.writerow(header)
            for r in rows:
                writer.writerow([
                    r.id, r.platform_id, r.platform_name, r.source_url, r.title, r.price_amount, r.price_currency,
                    r.location_text, r.bedrooms, r.bathrooms, r.size_value, r.size_unit,
                    r.agent_name, r.agency_name, r.agency_url, r.date_posted
                ])
        print('Exported', len(rows), 'listings to', csv_path)
    finally:
        db.close()

if __name__ == '__main__':
    out_path = os.path.join(os.path.dirname(__file__), 'listings_export.csv')
    export(out_path)
