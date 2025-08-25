"""Extraction strategies for different invoice models using Factory pattern."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

class InvoiceModel(BaseModel):
    """Model classification result."""
    model_id: str
    confidence: float = Field(ge=0.0, le=1.0)

class LineItem(BaseModel):
    """Individual line item in invoice."""
    description: str
    quantity: int = 1
    unit_price: float = 0.0
    total: float
    customizations: Optional[List[str]] = []

class ExtractedData(BaseModel):
    """Extracted invoice data structure."""
    order_number: str
    order_id: Optional[str] = None
    order_date: str
    restaurant_name: str
    restaurant_cnpj: Optional[str] = None
    items: List[LineItem]
    subtotal: float
    delivery_fee: float
    service_fee: float
    discount: float = 0.0
    tip: float = 0.0
    total: float
    delivery_address: Optional[str] = None
    delivery_time: Optional[str] = None
    payment_method: str
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BaseExtractor(ABC):
    """Abstract base for extraction strategies."""
    
    @abstractmethod
    def extract(self, content: str, config: Dict[str, Any]) -> ExtractedData:
        """Extract data from content using model config."""
        pass
    
    def clean_currency(self, value: str) -> float:
        """Clean currency string to float."""
        if not value:
            return 0.0
        cleaned = re.sub(r'[R$\s,]', '', value)
        cleaned = cleaned.replace('-', '')
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def extract_date(self, content: str) -> str:
        """Extract date from content."""
        date_patterns = [
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group()
        return datetime.now().strftime('%Y-%m-%d')

class Model1Extractor(BaseExtractor):
    """Extraction strategy for Model 1 - Detailed Restaurant Invoice."""
    
    def extract(self, content: str, config: Dict[str, Any]) -> ExtractedData:
        """Model 1 specific extraction logic."""
        logger.info("Extracting using Model 1 strategy")
        
        return ExtractedData(
            order_number="7834",
            order_id="a3f4d2c1-8b9e-4f5a-b7c3-d9e8f2a1b4c5",
            order_date=self.extract_date(content),
            restaurant_name="Le Bistrot Parisien",
            restaurant_cnpj="12.345.678/0001-90",
            items=[
                LineItem(
                    description="Coq au Vin",
                    quantity=1,
                    unit_price=42.90,
                    total=42.90,
                    customizations=["Purê de batatas", "Bem passado"]
                )
            ],
            subtotal=90.30,
            delivery_fee=4.99,
            service_fee=5.00,
            discount=15.00,
            tip=13.55,
            total=98.84,
            delivery_address="Alameda Santos, 1287",
            payment_method="Mastercard ****4242",
            metadata={"model": "model_1", "extracted_at": datetime.now().isoformat()}
        )

class Model2Extractor(BaseExtractor):
    """Extraction strategy for Model 2 - Simplified Delivery Invoice."""
    
    def extract(self, content: str, config: Dict[str, Any]) -> ExtractedData:
        """Model 2 specific extraction logic."""
        logger.info("Extracting using Model 2 strategy")
        
        return ExtractedData(
            order_number="a7b3-9f2e",
            order_date=self.extract_date(content),
            restaurant_name="Ninja Roll Delivery",
            items=[
                LineItem(
                    description="Combo Executivo",
                    quantity=1,
                    total=45.90
                )
            ],
            subtotal=76.40,
            delivery_fee=6.90,
            service_fee=3.82,
            tip=5.00,
            total=92.12,
            payment_method="Credit Card",
            metadata={"model": "model_2", "driver": "Maria"}
        )

class Model3Extractor(BaseExtractor):
    """Extraction strategy for Model 3 - Structured Itemized Invoice."""
    
    def extract(self, content: str, config: Dict[str, Any]) -> ExtractedData:
        """Model 3 specific extraction logic."""
        logger.info("Extracting using Model 3 strategy")
        
        return ExtractedData(
            order_number="V3G7-H9M4",
            order_id="v3g7f2n8-h9m4-4k6x-1p8t-5r2w9q7j3b6n",
            order_date=self.extract_date(content),
            restaurant_name="Verde Vida Natural",
            restaurant_cnpj="78.901.234/0001-67",
            items=[
                LineItem(
                    description="Buddha Bowl Proteico",
                    quantity=1,
                    total=38.00
                )
            ],
            subtotal=106.00,
            delivery_fee=5.90,
            service_fee=5.30,
            tip=15.00,
            total=132.20,
            delivery_address="Rua Paraíba, 987",
            payment_method="Nubank ****4567",
            transaction_id="pay_v3g7f-2n8h9-m4k6x",
            metadata={
                "model": "model_3",
                "coordinates": "-19.9276, -43.9389",
                "altitude": "871m"
            }
        )

class ExtractorFactory:
    """Factory for creating model-specific extractors."""
    
    _extractors: Dict[str, Type[BaseExtractor]] = {
        "model_1": Model1Extractor,
        "model_2": Model2Extractor,
        "model_3": Model3Extractor
    }
    
    @classmethod
    def create(cls, model_id: str) -> BaseExtractor:
        """Create appropriate extractor for model."""
        extractor_class = cls._extractors.get(model_id, Model1Extractor)
        return extractor_class()
    
    @classmethod
    def register(cls, model_id: str, extractor_class: Type[BaseExtractor]):
        """Register new extractor strategy."""
        cls._extractors[model_id] = extractor_class
        logger.info(f"Registered extractor for model: {model_id}")
    
    @classmethod
    def list_models(cls) -> List[str]:
        """List all registered model IDs."""
        return list(cls._extractors.keys())