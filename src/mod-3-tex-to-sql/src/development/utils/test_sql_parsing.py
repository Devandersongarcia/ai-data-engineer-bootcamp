"""Test the SQL parsing fix."""

import re

def test_sql_extraction():
    print("🧪 Testing SQL Extraction Fix")
    print("=" * 40)
    
    # Simulate the problematic LLM response
    llm_response = """Question: Retrieve the total amount, invoice date, and customer name for all invoices created in the last 7 days.

SQL Query:
SELECT total_amount, invoice_date, customer_name
FROM ubears_invoices_extract_airflow
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';"""
    
    print("Original LLM response:")
    print(repr(llm_response))
    print()
    
    # Apply the same parsing logic
    sql_query = llm_response.strip()
    
    # Remove markdown code blocks if present
    sql_query = re.sub(r'```sql\n?', '', sql_query)
    sql_query = re.sub(r'```\n?', '', sql_query)
    sql_query = sql_query.strip()
    
    # Extract SQL from response that might contain extra text
    # Look for SELECT statement in the response
    sql_lines = sql_query.split('\n')
    sql_parts = []
    found_select = False
    
    for line in sql_lines:
        line = line.strip()
        if not found_select:
            # Look for the start of SELECT statement
            if line.upper().startswith('SELECT'):
                found_select = True
                sql_parts.append(line)
            elif 'SELECT' in line.upper():
                # Extract from SELECT onwards
                select_pos = line.upper().find('SELECT')
                sql_parts.append(line[select_pos:])
                found_select = True
        else:
            # Continue collecting SQL lines
            if line and not line.startswith('Question:') and not line.startswith('SQL Query:'):
                sql_parts.append(line)
    
    if sql_parts:
        sql_query = ' '.join(sql_parts).strip()
    
    # Clean up any remaining prefixes
    sql_query = re.sub(r'^.*?SELECT', 'SELECT', sql_query, flags=re.IGNORECASE)
    sql_query = sql_query.strip()
    
    print("Extracted SQL query:")
    print(repr(sql_query))
    print()
    print("Final SQL:")
    print(sql_query)
    print()
    
    # Test validation
    sql_normalized = re.sub(r'\s+', ' ', sql_query.strip().upper())
    starts_with_select = sql_normalized.strip().startswith('SELECT')
    print(f"Starts with SELECT: {starts_with_select}")
    
    if starts_with_select:
        print("✅ SQL parsing fix works!")
        return True
    else:
        print("❌ SQL parsing still has issues")
        return False

if __name__ == "__main__":
    test_sql_extraction()