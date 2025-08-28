"""Check the full schema including database and schema names."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from sqlalchemy import create_engine, inspect, text

def check_full_schema():
    print("🔍 Checking Full Database Schema")
    print("=" * 50)
    
    settings = get_dev_settings()
    engine = create_engine(settings.database_url)
    
    print(f"Database URL: {settings.database_url}")
    print()
    
    # Check current database
    with engine.connect() as conn:
        try:
            # Get current database name
            db_result = conn.execute(text("SELECT current_database();"))
            current_db = db_result.fetchone()[0]
            print(f"📊 Current database: {current_db}")
            
            # Get current schema
            schema_result = conn.execute(text("SELECT current_schema();"))
            current_schema = schema_result.fetchone()[0]
            print(f"📋 Current schema: {current_schema}")
            
            # Check if table exists with full path
            table_check = conn.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE tablename LIKE '%ubears%' OR tablename LIKE '%invoice%'
                ORDER BY schemaname, tablename;
            """))
            
            print(f"\n🔍 Found invoice-related tables:")
            tables_found = []
            for row in table_check:
                schema_name, table_name = row
                full_table_name = f"{schema_name}.{table_name}"
                print(f"   📋 {full_table_name}")
                tables_found.append((schema_name, table_name, full_table_name))
            
            # Test the specific table
            if tables_found:
                schema_name, table_name, full_table_name = tables_found[0]
                
                print(f"\n🎯 Testing table access:")
                print(f"   Table: {full_table_name}")
                
                # Test count
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {full_table_name};"))
                    count = count_result.fetchone()[0]
                    print(f"   📈 Record count: {count}")
                    
                    if count > 0:
                        # Get sample data
                        sample_result = conn.execute(text(f"""
                            SELECT vendor_name, customer_name, total_amount, invoice_date
                            FROM {full_table_name} 
                            WHERE vendor_name IS NOT NULL 
                            LIMIT 5;
                        """))
                        
                        print(f"\n📝 Sample vendor names found:")
                        for row in sample_result:
                            vendor, customer, amount, date = row
                            print(f"   🍔 Vendor: {vendor}")
                            print(f"      Customer: {customer}")
                            print(f"      Amount: ${amount}")
                            print(f"      Date: {date}")
                            print()
                            
                except Exception as e:
                    print(f"   ❌ Error accessing table: {e}")
            
            # Check what our current schema detection returns
            print(f"\n🤖 What our TextToSQLConverter sees:")
            inspector = inspect(engine)
            detected_tables = inspector.get_table_names()
            print(f"   Detected tables: {detected_tables}")
            
            if detected_tables:
                table_name = detected_tables[0]
                columns = inspector.get_columns(table_name)
                print(f"   Columns in {table_name}: {len(columns)} columns")
                print(f"   Sample columns: {[col['name'] for col in columns[:5]]}")
            
        except Exception as e:
            print(f"❌ Error checking schema: {e}")

if __name__ == "__main__":
    check_full_schema()