"""Check the actual date ranges in the data."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from sqlalchemy import create_engine, text

def check_dates():
    print("📅 Checking Date Ranges in Data")
    print("=" * 40)
    
    settings = get_dev_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check date ranges
        date_query = text("""
            SELECT 
                MIN(created_at) as min_created,
                MAX(created_at) as max_created,
                MIN(invoice_date) as min_invoice_date,  
                MAX(invoice_date) as max_invoice_date,
                COUNT(*) as total_records,
                COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_7days,
                COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_30days,
                CURRENT_DATE as today
            FROM ubears_invoices_extract_airflow;
        """)
        
        result = conn.execute(date_query)
        row = result.fetchone()
        
        print(f"📊 Data Overview:")
        print(f"   Total records: {row.total_records}")
        print(f"   Today's date: {row.today}")
        print()
        print(f"📅 Created At Dates:")
        print(f"   Earliest: {row.min_created}")
        print(f"   Latest: {row.max_created}")
        print(f"   Last 7 days: {row.recent_7days} records")
        print(f"   Last 30 days: {row.recent_30days} records")
        print()
        print(f"📅 Invoice Dates:")
        print(f"   Earliest: {row.min_invoice_date}")
        print(f"   Latest: {row.max_invoice_date}")
        
        # Get some sample records with dates
        sample_query = text("""
            SELECT vendor_name, invoice_date, created_at, total_amount
            FROM ubears_invoices_extract_airflow
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        
        print(f"\n📝 Sample Records (newest first):")
        sample_result = conn.execute(sample_query)
        for row in sample_result:
            vendor = row.vendor_name or "No vendor"
            invoice_date = row.invoice_date or "No date"
            created_at = row.created_at or "No created"
            amount = row.total_amount or 0
            print(f"   🍔 {vendor}")
            print(f"      Invoice Date: {invoice_date}")
            print(f"      Created: {created_at}")
            print(f"      Amount: ${amount}")
            print()

if __name__ == "__main__":
    check_dates()