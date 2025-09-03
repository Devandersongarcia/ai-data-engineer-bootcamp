# src/tools/communication_tools.py - Communication Tools for UberEats Agents
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from agno.tools import Function
from pydantic import BaseModel, Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


class SMSInput(BaseModel):
    """Input schema for SMS messages"""
    to: str = Field(..., description="Phone number to send SMS to (E.164 format)")
    message: str = Field(..., description="SMS message content")
    from_number: Optional[str] = Field(default=None, description="Sender phone number")


class EmailInput(BaseModel):
    """Input schema for email messages"""
    to: List[str] = Field(..., description="List of recipient email addresses")
    subject: str = Field(..., description="Email subject line")
    message: str = Field(..., description="Email message content")
    html: bool = Field(default=False, description="Whether message is HTML format")


class SlackInput(BaseModel):
    """Input schema for Slack messages"""
    channel: str = Field(..., description="Slack channel or user to send message to")
    message: str = Field(..., description="Slack message content")
    thread_ts: Optional[str] = Field(default=None, description="Thread timestamp for replies")


class SMSTool(Function):
    """
    SMS communication tool using Twilio API
    
    Enables agents to:
    - Send delivery notifications to customers
    - Alert drivers about new orders
    - Send ETA updates
    - Notify about order delays
    """
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None):
        super().__init__(
            name="sms_tool",
            description="Send SMS messages for customer and driver notifications",
            input_schema=SMSInput
        )
        # In a real implementation, you'd get these from environment variables
        self.account_sid = account_sid or getattr(settings, 'twilio_account_sid', None)
        self.auth_token = auth_token or getattr(settings, 'twilio_auth_token', None)
        self.from_number = getattr(settings, 'twilio_phone_number', '+1234567890')
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS message"""
        try:
            sms_input = SMSInput(**input_data)
            
            # For demo purposes, we'll simulate SMS sending
            # In production, you'd integrate with Twilio API:
            # 
            # from twilio.rest import Client
            # client = Client(self.account_sid, self.auth_token)
            # 
            # message = client.messages.create(
            #     body=sms_input.message,
            #     from_=sms_input.from_number or self.from_number,
            #     to=sms_input.to
            # )
            
            # Simulate successful SMS sending
            logger.info(f"SMS sent to {sms_input.to}: {sms_input.message}")
            
            return {
                "success": True,
                "to": sms_input.to,
                "message": sms_input.message,
                "status": "sent",
                "provider": "twilio",
                "message_id": f"sim_msg_{hash(sms_input.message)}"
            }
            
        except Exception as e:
            logger.error(f"SMS sending error: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": input_data.get("to", "unknown")
            }


class EmailTool(Function):
    """
    Email communication tool for order confirmations and updates
    
    Enables agents to:
    - Send order confirmations
    - Email delivery receipts  
    - Send promotional offers
    - Notify about order issues
    """
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        super().__init__(
            name="email_tool",
            description="Send email notifications for orders and updates",
            input_schema=EmailInput
        )
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = getattr(settings, 'email_user', 'ubereats@example.com')
        self.email_password = getattr(settings, 'email_password', '')
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email message"""
        try:
            email_input = EmailInput(**input_data)
            
            # For demo purposes, we'll simulate email sending
            # In production, you'd use SMTP or email service API:
            #
            # msg = MIMEMultipart()
            # msg['From'] = self.email_user
            # msg['To'] = ', '.join(email_input.to)
            # msg['Subject'] = email_input.subject
            # 
            # msg.attach(MIMEText(email_input.message, 'html' if email_input.html else 'plain'))
            # 
            # server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            # server.starttls()
            # server.login(self.email_user, self.email_password)
            # server.send_message(msg)
            # server.quit()
            
            # Simulate successful email sending
            logger.info(f"Email sent to {email_input.to}: {email_input.subject}")
            
            return {
                "success": True,
                "to": email_input.to,
                "subject": email_input.subject,
                "message_length": len(email_input.message),
                "format": "html" if email_input.html else "text",
                "status": "sent",
                "message_id": f"email_{hash(email_input.subject)}"
            }
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": input_data.get("to", [])
            }


class SlackTool(Function):
    """
    Slack integration tool for team notifications
    
    Enables agents to:
    - Alert operations team to issues
    - Send driver shortage notifications
    - Report system performance alerts
    - Coordinate incident response
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        super().__init__(
            name="slack_tool",
            description="Send Slack notifications to team channels",
            input_schema=SlackInput
        )
        self.bot_token = bot_token or getattr(settings, 'slack_bot_token', None)
        self.slack_api_url = "https://slack.com/api/chat.postMessage"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack message"""
        try:
            slack_input = SlackInput(**input_data)
            
            if not self.bot_token:
                # Simulate Slack message for demo
                logger.info(f"Slack message to {slack_input.channel}: {slack_input.message}")
                return {
                    "success": True,
                    "channel": slack_input.channel,
                    "message": slack_input.message,
                    "status": "sent",
                    "ts": f"sim_ts_{hash(slack_input.message)}",
                    "provider": "slack_simulation"
                }
            
            # For production, use Slack Web API:
            # headers = {
            #     "Authorization": f"Bearer {self.bot_token}",
            #     "Content-Type": "application/json"
            # }
            # 
            # payload = {
            #     "channel": slack_input.channel,
            #     "text": slack_input.message
            # }
            # 
            # if slack_input.thread_ts:
            #     payload["thread_ts"] = slack_input.thread_ts
            # 
            # response = requests.post(self.slack_api_url, json=payload, headers=headers)
            # result = response.json()
            
            # Simulate successful Slack sending
            logger.info(f"Slack message sent to {slack_input.channel}: {slack_input.message}")
            
            return {
                "success": True,
                "channel": slack_input.channel,
                "message": slack_input.message,
                "status": "sent",
                "ts": f"slack_ts_{hash(slack_input.message)}"
            }
            
        except Exception as e:
            logger.error(f"Slack sending error: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": input_data.get("channel", "unknown")
            }


# Pre-configured tool instances
sms_tool = SMSTool()
email_tool = EmailTool()
slack_tool = SlackTool()

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

def get_message_template(template_name: str, message_type: str = "sms") -> Optional[str]:
    """Get pre-defined message template"""
    template = MESSAGE_TEMPLATES.get(template_name, {})
    if isinstance(template, dict):
        return template.get(message_type)
    return template

def format_message_template(template: str, **kwargs) -> str:
    """Format message template with variables"""
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing template variable: {e}")
        return template