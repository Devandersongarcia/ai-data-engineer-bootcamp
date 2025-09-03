# src/tools/communication_tools_v2.py - Communication Tools for UberEats Agents (Agno Compatible)
import logging
from typing import Dict, Any, List, Optional
from agno.tools import function
from pydantic import Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


@function
def send_sms(
    to: str = Field(..., description="Phone number to send SMS to (E.164 format)"),
    message: str = Field(..., description="SMS message content"),
    from_number: Optional[str] = Field(default=None, description="Sender phone number")
) -> Dict[str, Any]:
    """
    Send SMS messages for customer and driver notifications
    
    Enables agents to:
    - Send delivery notifications to customers
    - Alert drivers about new orders
    - Send ETA updates
    - Notify about order delays
    """
    try:
        # For demo purposes, simulate SMS sending
        logger.info(f"SMS sent to {to}: {message}")
        
        return {
            "success": True,
            "to": to,
            "message": message,
            "status": "sent",
            "provider": "twilio_simulation",
            "message_id": f"sim_msg_{hash(message)}"
        }
        
    except Exception as e:
        logger.error(f"SMS sending error: {e}")
        return {
            "success": False,
            "error": str(e),
            "to": to
        }


@function
def send_email(
    to: List[str] = Field(..., description="List of recipient email addresses"),
    subject: str = Field(..., description="Email subject line"),
    message: str = Field(..., description="Email message content"),
    html: bool = Field(default=False, description="Whether message is HTML format")
) -> Dict[str, Any]:
    """
    Send email notifications for orders and updates
    
    Enables agents to:
    - Send order confirmations
    - Email delivery receipts  
    - Send promotional offers
    - Notify about order issues
    """
    try:
        # For demo purposes, simulate email sending
        logger.info(f"Email sent to {to}: {subject}")
        
        return {
            "success": True,
            "to": to,
            "subject": subject,
            "message_length": len(message),
            "format": "html" if html else "text",
            "status": "sent",
            "message_id": f"email_{hash(subject)}"
        }
        
    except Exception as e:
        logger.error(f"Email sending error: {e}")
        return {
            "success": False,
            "error": str(e),
            "to": to
        }


@function
def send_slack_message(
    channel: str = Field(..., description="Slack channel or user to send message to"),
    message: str = Field(..., description="Slack message content"),
    thread_ts: Optional[str] = Field(default=None, description="Thread timestamp for replies")
) -> Dict[str, Any]:
    """
    Send Slack notifications to team channels
    
    Enables agents to:
    - Alert operations team to issues
    - Send driver shortage notifications
    - Report system performance alerts
    - Coordinate incident response
    """
    try:
        # For demo purposes, simulate Slack message
        logger.info(f"Slack message to {channel}: {message}")
        
        return {
            "success": True,
            "channel": channel,
            "message": message,
            "status": "sent",
            "ts": f"sim_ts_{hash(message)}",
            "provider": "slack_simulation"
        }
        
    except Exception as e:
        logger.error(f"Slack sending error: {e}")
        return {
            "success": False,
            "error": str(e),
            "channel": channel
        }


# Pre-defined message templates for UberEats use cases
MESSAGE_TEMPLATES = {
    "order_confirmation": {
        "sms": "Hi {customer_name}! Your order #{order_id} from {restaurant_name} has been confirmed. Estimated delivery: {eta}. Track your order: {tracking_url}",
        "email": {
            "subject": "Order Confirmation - {restaurant_name}",
            "body": """
            <h2>Order Confirmed!</h2>
            <p>Hi {customer_name},</p>
            <p>Your order #{order_id} from {restaurant_name} has been confirmed.</p>
            <p><strong>Estimated delivery time:</strong> {eta}</p>
            <p><strong>Order total:</strong> ${total_amount}</p>
            <p>You can track your order at: {tracking_url}</p>
            <p>Thank you for choosing UberEats!</p>
            """
        }
    },
    
    "driver_assignment": {
        "sms": "New pickup available! Order #{order_id} at {restaurant_name}, {restaurant_address}. Pickup by {pickup_time}. Accept? Reply YES/NO"
    },
    
    "eta_update": {
        "sms": "Update: Your order #{order_id} ETA has changed to {new_eta} due to {reason}. Thanks for your patience!"
    },
    
    "order_delay": {
        "sms": "Sorry, your order #{order_id} is delayed by {delay_minutes} minutes due to {reason}. New ETA: {new_eta}",
        "slack": "🚨 Order #{order_id} delayed by {delay_minutes} minutes. Reason: {reason}. Customer notified."
    },
    
    "driver_shortage": {
        "slack": "⚠️ Driver shortage alert in {area}! {pending_orders} orders waiting. Average wait time: {avg_wait_time} minutes."
    },
    
    "system_alert": {
        "slack": "🔴 System Alert: {alert_type} - {description}. Requires immediate attention. {details}"
    }
}


@function
def get_message_template(
    template_name: str = Field(..., description="Name of the message template"),
    message_type: str = Field(default="sms", description="Type of message: sms, email, slack")
) -> Dict[str, Any]:
    """Get pre-defined message template for UberEats communications"""
    try:
        template = MESSAGE_TEMPLATES.get(template_name, {})
        
        if isinstance(template, dict):
            message_template = template.get(message_type)
        else:
            message_template = template
        
        if message_template:
            return {
                "success": True,
                "template_name": template_name,
                "message_type": message_type,
                "template": message_template
            }
        else:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found for type '{message_type}'",
                "available_templates": list(MESSAGE_TEMPLATES.keys())
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@function
def format_message_template(
    template: str = Field(..., description="Message template with placeholders"),
    **kwargs
) -> Dict[str, Any]:
    """Format message template with variables"""
    try:
        formatted_message = template.format(**kwargs)
        return {
            "success": True,
            "original_template": template,
            "formatted_message": formatted_message,
            "variables_used": list(kwargs.keys())
        }
    except KeyError as e:
        missing_var = str(e).strip("'")
        return {
            "success": False,
            "error": f"Missing template variable: {missing_var}",
            "template": template,
            "provided_variables": list(kwargs.keys())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }