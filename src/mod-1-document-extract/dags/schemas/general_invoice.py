# schemas/general_invoice.py
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from enum import Enum

class InvoiceType(str, Enum):
    STANDARD = "standard"
    PROFORMA = "proforma"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    RECEIPT = "receipt"
    UBER_EATS = "uber_eats"
    DELIVERY = "delivery"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    OTHER = "other"

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    BRL = "BRL"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"

class Address(BaseModel):
    """Schema for address information"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    full_address: Optional[str] = None

class ContactInfo(BaseModel):
    """Schema for contact information"""
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

class TaxInfo(BaseModel):
    """Schema for tax identification"""
    tax_id: Optional[str] = None
    vat_number: Optional[str] = None
    registration_number: Optional[str] = None

class Entity(BaseModel):
    """Schema for vendor/customer entity"""
    name: Optional[str] = None
    address: Optional[Address] = None
    contact: Optional[ContactInfo] = None
    tax_info: Optional[TaxInfo] = None

class LineItemModifier(BaseModel):
    """Schema for line item modifications"""
    name: str
    value: Optional[str] = None
    extra_cost: Optional[Decimal] = Field(default=Decimal("0.00"))

class LineItem(BaseModel):
    """Schema for invoice line items"""
    description: str
    quantity: Optional[Decimal] = Field(default=Decimal("1"))
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = Field(default=Decimal("0.00"))
    discount_amount: Optional[Decimal] = Field(default=Decimal("0.00"))
    modifiers: List[LineItemModifier] = Field(default_factory=list)
    product_code: Optional[str] = None
    category: Optional[str] = None

class PaymentSummary(BaseModel):
    """Schema for payment breakdown"""
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    shipping_amount: Optional[Decimal] = None
    tip_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    amount_due: Optional[Decimal] = None
    currency: Optional[Currency] = None

class PaymentDetails(BaseModel):
    """Schema for payment information"""
    method: Optional[PaymentMethod] = None
    terms: Optional[str] = None
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    transaction_id: Optional[str] = None
    reference_number: Optional[str] = None

class DeliveryInfo(BaseModel):
    """Schema for delivery information (for delivery invoices)"""
    status: Optional[str] = None
    delivery_address: Optional[Address] = None
    tracking_id: Optional[str] = None
    delivery_time_minutes: Optional[int] = None
    distance_km: Optional[float] = None
    driver_name: Optional[str] = None
    driver_id: Optional[str] = None

class GeneralInvoice(BaseModel):
    """Main schema for general invoice data"""
    # Document identification
    invoice_number: Optional[str] = None
    invoice_type: Optional[InvoiceType] = InvoiceType.STANDARD
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    issue_date: Optional[date] = None
    
    # Business entities
    vendor: Optional[Entity] = None
    customer: Optional[Entity] = None
    
    # Line items
    line_items: List[LineItem] = Field(default_factory=list)
    
    # Financial summary
    payment_summary: Optional[PaymentSummary] = None
    
    # Payment information
    payment_details: Optional[PaymentDetails] = None
    
    # Delivery information (for delivery services)
    delivery_info: Optional[DeliveryInfo] = None
    
    # Additional fields
    purchase_order_number: Optional[str] = None
    project_code: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    
    # Metadata
    extraction_confidence: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    source_file: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @validator('extraction_confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        if v is not None:
            return max(0.0, min(1.0, float(v)))
        return 0.0
    
    @validator('invoice_date', 'due_date', 'issue_date', pre=True)
    def parse_dates(cls, v):
        """Parse date strings to date objects"""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                try:
                    return datetime.strptime(v, "%m/%d/%Y").date()
                except ValueError:
                    try:
                        return datetime.strptime(v, "%d/%m/%Y").date()
                    except ValueError:
                        return None
        return v

    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for database insertion"""
        result = {}
        
        # Basic fields
        result['invoice_number'] = self.invoice_number
        result['invoice_type'] = self.invoice_type.value if self.invoice_type else None
        result['invoice_date'] = self.invoice_date
        result['due_date'] = self.due_date
        result['issue_date'] = self.issue_date
        result['purchase_order_number'] = self.purchase_order_number
        result['project_code'] = self.project_code
        result['department'] = self.department
        result['description'] = self.description
        result['notes'] = self.notes
        
        # Vendor information
        if self.vendor:
            result['vendor_name'] = self.vendor.name
            if self.vendor.address:
                result['vendor_address'] = self.vendor.address.full_address
                result['vendor_city'] = self.vendor.address.city
                result['vendor_state'] = self.vendor.address.state
                result['vendor_zip'] = self.vendor.address.zip_code
                result['vendor_country'] = self.vendor.address.country
            if self.vendor.contact:
                result['vendor_phone'] = self.vendor.contact.phone
                result['vendor_email'] = self.vendor.contact.email
            if self.vendor.tax_info:
                result['vendor_tax_id'] = self.vendor.tax_info.tax_id
        
        # Customer information
        if self.customer:
            result['customer_name'] = self.customer.name
            if self.customer.address:
                result['customer_address'] = self.customer.address.full_address
                result['customer_city'] = self.customer.address.city
                result['customer_state'] = self.customer.address.state
                result['customer_zip'] = self.customer.address.zip_code
                result['customer_country'] = self.customer.address.country
            if self.customer.contact:
                result['customer_phone'] = self.customer.contact.phone
                result['customer_email'] = self.customer.contact.email
            if self.customer.tax_info:
                result['customer_tax_id'] = self.customer.tax_info.tax_id
        
        # Payment summary
        if self.payment_summary:
            result['subtotal_amount'] = self.payment_summary.subtotal
            result['tax_amount'] = self.payment_summary.tax_amount
            result['discount_amount'] = self.payment_summary.discount_amount
            result['shipping_amount'] = self.payment_summary.shipping_amount
            result['total_amount'] = self.payment_summary.total_amount
            result['amount_paid'] = self.payment_summary.amount_paid
            result['amount_due'] = self.payment_summary.amount_due
            result['currency'] = self.payment_summary.currency.value if self.payment_summary.currency else None
        
        # Payment details
        if self.payment_details:
            result['payment_method'] = self.payment_details.method.value if self.payment_details.method else None
            result['payment_terms'] = self.payment_details.terms
        
        # Metadata
        result['extraction_confidence'] = self.extraction_confidence
        result['extracted_at'] = self.extracted_at
        result['source_file'] = self.source_file
        result['line_items'] = [item.dict() for item in self.line_items]
        result['raw_extracted_data'] = self.raw_data
        
        return result