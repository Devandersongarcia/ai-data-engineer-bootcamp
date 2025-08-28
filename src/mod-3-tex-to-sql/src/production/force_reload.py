#!/usr/bin/env python3
"""
Force reload script to clear Python module cache
Run this before starting your Streamlit app if you suspect caching issues
"""

import sys
import os

def clear_module_cache():
    """Clear Python module cache for our project"""
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"🔄 Clearing module cache for: {current_dir}")
    
    # List of modules to clear (our project modules)
    modules_to_clear = []
    
    for module_name in list(sys.modules.keys()):
        if any(keyword in module_name for keyword in ['core', 'config', 'utils', 'apps', 'vanna_converter']):
            modules_to_clear.append(module_name)
    
    print(f"📦 Found {len(modules_to_clear)} modules to clear:")
    for module in modules_to_clear[:10]:  # Show first 10
        print(f"   - {module}")
    if len(modules_to_clear) > 10:
        print(f"   ... and {len(modules_to_clear) - 10} more")
    
    # Clear the modules
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]
            print(f"✅ Cleared: {module_name}")
    
    print(f"🎉 Cache clearing complete!")
    print(f"💡 Now restart your Streamlit app")

if __name__ == "__main__":
    clear_module_cache()