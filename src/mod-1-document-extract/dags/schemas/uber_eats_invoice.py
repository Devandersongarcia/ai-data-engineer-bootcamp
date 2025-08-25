# schemas/uber_eats_invoice.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    PIX = "pix"

class OrderItemModifier(BaseModel):
    """Schema for item modifications/customizations"""
    name: str
    value: str
    extra_cost: Optional[Decimal] = Field(default=Decimal("0.00"))

class OrderItem(BaseModel):
    """Schema for individual order items"""
    quantity: int
    name: str
    modifiers: List[OrderItemModifier] = Field(default_factory=list)
    unit_price: Decimal
    total_price: Decimal

class Restaurant(BaseModel):
    """Schema for restaurant information"""
    name: str
    rating: float
    review_count: int
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    cnpj: Optional[str] = None  # Brazilian tax ID
    cuisine_type: str
    operating_hours: str
    uuid: str

class DeliveryDetails(BaseModel):
    """Schema for delivery information"""
    status: str
    delivery_address: str
    delivery_city: str
    delivery_state: str
    delivery_zip: str
    customer_cpf_masked: str
    gps_tracking_id: str
    delivery_time_minutes: int
    distance_km: float
    driver_name: str
    driver_id: str

class PaymentSummary(BaseModel):
    """Schema for payment breakdown"""
    subtotal: Decimal
    delivery_fee: Decimal
    service_fee: Decimal
    promotional_discount: Decimal
    tip_amount: Decimal
    tip_recipient: str
    tip_recipient_id: str
    total: Decimal

class PaymentDetails(BaseModel):
    """Schema for payment method details"""
    method: PaymentMethod
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    transaction_id: str

class UberEatsInvoice(BaseModel):
    """Main schema for Uber Eats invoice"""
    # Order identification
    order_number: str
    order_id: str
    order_datetime: datetime
    
    # Restaurant information
    restaurant: Restaurant
    
    # Order items
    items: List[OrderItem]
    
    # Payment summary
    payment_summary: PaymentSummary
    
    # Delivery details
    delivery: DeliveryDetails
    
    # Payment method
    payment_details: PaymentDetails
    
    # Metadata
    rating_code: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    source_file: Optional[str] = None