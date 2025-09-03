from agno.tools import tool
from pydantic import Field

@tool
def test_func(x: int = Field(..., description="test parameter")):
    """Test function"""
    return {"result": x * 2}

print(f"Type: {type(test_func)}")
print(f"Name: {test_func.name}")
print(f"Description: {test_func.description}")

# Try to execute it
try:
    result = test_func(5)
    print(f"Direct call result: {result}")
except Exception as e:
    print(f"Direct call error: {e}")

# Try the execute method
try:
    result = test_func.execute({"x": 5})
    print(f"Execute method result: {result}")
except Exception as e:
    print(f"Execute method error: {e}")

# Check if it has other methods
print(f"Methods: {[m for m in dir(test_func) if not m.startswith('_')]}")