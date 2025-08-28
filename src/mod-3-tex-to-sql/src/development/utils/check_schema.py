"""Check actual database schema to get correct table names."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from sqlalchemy import create_engine, inspect

def check_schema():
    settings = get_dev_settings()
    engine = create_engine(settings.database_url)
    
    print("🔍 Checking actual database schema...")
    print("=" * 50)
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    print(f"📊 Found {len(table_names)} tables in database:")
    for table in table_names:
        print(f"   ✅ {table}")
    
    if "ubears_invoices_extract_airflow" in table_names:
        print(f"\n🎯 Found your table: ubears_invoices_extract_airflow")
        
        print("\n📋 Columns in ubears_invoices_extract_airflow:")
        columns = inspector.get_columns("ubears_invoices_extract_airflow")
        for col in columns:
            col_type = str(col["type"])
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"   • {col['name']}: {col_type} {nullable}")
            
        # Check for a few sample records
        try:
            with engine.connect() as conn:
                result = conn.execute("SELECT COUNT(*) FROM ubears_invoices_extract_airflow")
                count = result.fetchone()[0]
                print(f"\n📈 Records in table: {count}")
                
                if count > 0:
                    sample = conn.execute("SELECT * FROM ubears_invoices_extract_airflow LIMIT 3")
                    print("\n📝 Sample records:")
                    for i, row in enumerate(sample, 1):
                        print(f"   Row {i}: {dict(row)}")
                        
        except Exception as e:
            print(f"\n⚠️ Could not sample data: {e}")
            
    else:
        print("\n❌ Table ubears_invoices_extract_airflow not found")
        print("\n🔍 Available tables:")
        for table in table_names:
            print(f"   {table}")

if __name__ == "__main__":
    check_schema()