"""Data models for invoice processing using Pydantic."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class InvoiceModel(BaseModel):
    """Model classification result from LLM."""
    model_id: str = Field(..., description="Identified model ID (model_1, model_2, or model_3)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score of classification")
    reasoning: Optional[str] = Field(None, description="LLM's reasoning for the classification")

class LineItem(BaseModel):
    """Individual line item in an invoice."""
    description: str = Field(..., description="Item description")
    quantity: int = Field(1, description="Quantity ordered")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total: float = Field(..., description="Total price for this item")
    customizations: Optional[List[str]] = Field(default_factory=list, description="Item customizations")

class ExtractedInvoice(BaseModel):
    """Complete structured representation of an extracted invoice.
    
    What: Contains all extracted invoice data in a validated structure.
    Why: Provides consistent schema across different invoice formats.
    How: LLM populates fields based on model-specific extraction rules.
    
    The model supports three invoice formats:
    - Model 1: Detailed restaurant invoices with CNPJ/UUID
    - Model 2: Simplified delivery format with driver info
    - Model 3: Structured format with geographic data
    """
    order_number: str = Field(..., description="Order/Invoice number")
    order_date: str = Field(..., description="Order date")
    restaurant_name: str = Field(..., description="Restaurant/Vendor name")
    items: List[LineItem] = Field(..., description="Line items")
    subtotal: float = Field(..., description="Subtotal before fees")
    delivery_fee: float = Field(0.0, description="Delivery fee")
    service_fee: float = Field(0.0, description="Service fee")
    total: float = Field(..., description="Total amount")

    order_id: Optional[str] = Field(None, description="Unique order ID/UUID")
    restaurant_cnpj: Optional[str] = Field(None, description="Restaurant CNPJ (Brazilian tax ID)")
    restaurant_address: Optional[str] = Field(None, description="Restaurant address")
    discount: float = Field(0.0, description="Discount amount")
    tip: float = Field(0.0, description="Tip amount")
    delivery_address: Optional[str] = Field(None, description="Delivery address")
    delivery_time: Optional[str] = Field(None, description="Delivery time/duration")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    transaction_id: Optional[str] = Field(None, description="Payment transaction ID")

    driver_name: Optional[str] = Field(None, description="Delivery driver name")
    driver_id: Optional[str] = Field(None, description="Driver ID")
    delivery_distance: Optional[str] = Field(None, description="Delivery distance")
    delivery_speed: Optional[str] = Field(None, description="Average delivery speed")
    coordinates: Optional[str] = Field(None, description="GPS coordinates")
    altitude: Optional[str] = Field(None, description="Altitude")

    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")