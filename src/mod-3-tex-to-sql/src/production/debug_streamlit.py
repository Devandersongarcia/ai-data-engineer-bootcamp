#!/usr/bin/env python3
"""
Debug script to test Vanna.ai functionality in Streamlit environment
Run this with: streamlit run debug_streamlit.py
"""

import streamlit as st
import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

st.title("🔍 Vanna.ai Debug Interface")
st.write("Testing the fixed _is_explanatory_response method")

try:
    from core.vanna_converter import VannaTextToSQLConverter
    
    # Test the method directly
    st.subheader("1. Testing _is_explanatory_response method")
    
    converter = VannaTextToSQLConverter.__new__(VannaTextToSQLConverter)
    
    # Test cases
    test_cases = [
        ("-- intermediate_sql\n\nSELECT DISTINCT payment_method FROM payments;", "Should be FALSE"),
        ("SELECT * FROM payments LIMIT 10;", "Should be FALSE"),
        ("I need more information to help you", "Should be TRUE"),
        ("Por favor, forneça mais detalhes", "Should be TRUE")
    ]
    
    for test_response, expected in test_cases:
        is_explanatory = converter._is_explanatory_response(test_response)
        status = "✅" if (expected == "Should be FALSE" and not is_explanatory) or (expected == "Should be TRUE" and is_explanatory) else "❌"
        
        st.write(f"{status} **{expected}**: `{is_explanatory}`")
        st.code(test_response[:50] + "..." if len(test_response) > 50 else test_response)
    
    # Test full converter
    st.subheader("2. Testing Full Converter")
    
    if st.button("Test Full Conversion"):
        try:
            full_converter = VannaTextToSQLConverter(
                database_url=os.getenv('DATABASE_URL', 'postgresql://postgres:123456@localhost:5432/postgres'),
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            
            test_question = "agora quero saber quais são os metodos de pagamento disponiveis"
            
            with st.spinner("Converting question to SQL..."):
                result = full_converter.convert_to_sql(test_question)
            
            st.write("**Result:**")
            st.json(result)
            
            if result['success']:
                st.success("✅ SQL Generation Successful!")
                st.code(result['sql_query'], language='sql')
            else:
                st.error(f"❌ Failed: {result['error']}")
                if result.get('sql_query'):
                    st.write("**Raw Response:**")
                    st.code(result['sql_query'])
                    
        except Exception as e:
            st.error(f"Exception: {e}")
            st.write("**Full Error:**")
            st.exception(e)
    
    # Environment info
    st.subheader("3. Environment Information")
    st.write(f"**Python Path**: {sys.path[0]}")
    st.write(f"**Working Directory**: {os.getcwd()}")
    st.write(f"**Current File Directory**: {current_dir}")
    st.write(f"**Python Version**: {sys.version}")
    
    # Check if we can access the method
    import inspect
    method_source = inspect.getsource(converter._is_explanatory_response)
    st.subheader("4. Current Method Source (First 500 chars)")
    st.code(method_source[:500] + "..." if len(method_source) > 500 else method_source)
    
    # Check if the fix is in the source
    if "intermediate_sql" in method_source:
        st.success("✅ Fix is present in the method source!")
    else:
        st.error("❌ Fix is NOT present in the method source!")

except Exception as e:
    st.error(f"Failed to import or test: {e}")
    st.exception(e)

st.write("---")
st.write("**Instructions:**")
st.write("1. If you see ✅ for all test cases, the fix is working")
st.write("2. If you see ❌, there's still an issue with the method")
st.write("3. Click 'Test Full Conversion' to test the complete pipeline")