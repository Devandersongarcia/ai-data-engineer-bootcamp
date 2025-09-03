# UberEats Agent Tools Package
from .database_tools import PostgresTool, RedisTool
from .communication_tools import SMSTool, EmailTool, SlackTool
from .maps_tools import GoogleMapsTool, WeatherTool
from .analytics_tools import PandasTool, CalculatorTool

# Pre-configured tool instances for easy use
postgres_tool = PostgresTool()
redis_tool = RedisTool()
sms_tool = SMSTool()
email_tool = EmailTool()
slack_tool = SlackTool()
google_maps_tool = GoogleMapsTool()
weather_tool = WeatherTool()
pandas_tool = PandasTool()
calculator_tool = CalculatorTool()

__all__ = [
    "PostgresTool", "RedisTool",
    "SMSTool", "EmailTool", "SlackTool", 
    "GoogleMapsTool", "WeatherTool",
    "PandasTool", "CalculatorTool",
    # Pre-configured instances
    "postgres_tool", "redis_tool", "sms_tool", "email_tool", "slack_tool",
    "google_maps_tool", "weather_tool", "pandas_tool", "calculator_tool"
]