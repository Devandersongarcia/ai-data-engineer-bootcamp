"""Langfuse integration service for prompt management and tracing."""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from config.settings import DevSettings
from utils.logging_utils import get_logger

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

logger = get_logger(__name__)


@dataclass
class PromptTemplate:
    """Structured representation of a prompt template.
    
    Attributes:
        name: Unique identifier for the prompt
        content: Template content with variable placeholders
        variables: List of required variable names
        version: Optional version identifier
        labels: Optional list of labels for categorization
        config: Optional configuration parameters
    """
    name: str
    content: str
    variables: List[str]
    version: Optional[str] = None
    labels: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class LangfuseService:
    """Centralized service for Langfuse prompt management and monitoring.
    
    This service provides a robust interface for managing prompts through Langfuse,
    with comprehensive error handling and fallback mechanisms.
    """
    
    def __init__(self, settings: DevSettings):
        """Initialize Langfuse service with comprehensive configuration validation.
        
        Args:
            settings: Development environment settings
        """
        self.settings = settings
        self.client = None
        self.enabled = self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """Initialize Langfuse service with proper error handling.
        
        Returns:
            True if service is successfully initialized, False otherwise
        """
        if not LANGFUSE_AVAILABLE:
            logger.warning("Langfuse SDK not available. Install with: pip install langfuse")
            return False
        
        if not self.settings.langfuse_enabled:
            logger.info("Langfuse service disabled in configuration")
            return False
        
        if not self._validate_credentials():
            logger.warning("Langfuse credentials not configured properly")
            return False
        
        return self._create_client()
    
    def _validate_credentials(self) -> bool:
        """Validate Langfuse credentials are properly configured."""
        return bool(
            self.settings.langfuse_secret_key and 
            self.settings.langfuse_public_key
        )
    
    def _create_client(self) -> bool:
        """Create Langfuse client with error handling."""
        try:
            self.client = Langfuse(
                secret_key=self.settings.langfuse_secret_key,
                public_key=self.settings.langfuse_public_key,
                host=self.settings.langfuse_host
            )
            logger.info("Langfuse client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")
            return False
    
    def get_prompt(
        self, 
        name: str, 
        variables: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None, 
        label: Optional[str] = None
    ) -> Optional[str]:
        """Retrieve and compile a prompt from Langfuse with robust error handling.
        
        Args:
            name: Prompt identifier
            variables: Template variables for compilation
            version: Specific version to retrieve
            label: Label-based retrieval (e.g., "production")
            
        Returns:
            Compiled prompt string or None if retrieval fails
        """
        if not self.is_available():
            logger.debug(f"Langfuse unavailable for prompt '{name}'")
            return None
        
        try:
            prompt = self._fetch_prompt(name, version, label)
            if not prompt:
                return None
            
            return self._compile_prompt(prompt, variables, name)
            
        except Exception as e:
            logger.error(f"Error retrieving prompt '{name}': {e}")
            return None
    
    def _fetch_prompt(self, name: str, version: Optional[str], label: Optional[str]):
        """Fetch prompt from Langfuse using specified parameters."""
        if version:
            return self.client.get_prompt(name=name, version=version)
        elif label:
            return self.client.get_prompt(name=name, label=label)
        else:
            return self.client.get_prompt(name=name)
    
    def _compile_prompt(
        self, 
        prompt, 
        variables: Optional[Dict[str, Any]], 
        name: str
    ) -> str:
        """Compile prompt with variables using fallback strategy."""
        if not variables:
            return prompt.prompt
        
        # Try Langfuse native compilation first
        try:
            compiled = prompt.compile(**variables)
            # Verify compilation worked
            if not any(f"{{{key}}}" in compiled for key in variables.keys()):
                logger.debug(f"Successfully compiled prompt '{name}' using Langfuse")
                return compiled
        except Exception as e:
            logger.debug(f"Langfuse compilation failed for '{name}': {e}")
        
        # Fallback to manual string replacement
        compiled = prompt.prompt
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            compiled = compiled.replace(placeholder, str(value))
        
        logger.debug(f"Compiled prompt '{name}' using manual replacement")
        return compiled
    
    def create_prompt(self, prompt: PromptTemplate) -> bool:
        """Create a new prompt in Langfuse with validation.
        
        Args:
            prompt: Complete prompt template to create
            
        Returns:
            True if creation successful, False otherwise
        """
        if not self.is_available():
            logger.debug("Langfuse unavailable for prompt creation")
            return False
        
        if not self._validate_prompt_template(prompt):
            return False
        
        try:
            self.client.create_prompt(
                name=prompt.name,
                prompt=prompt.content,
                labels=prompt.labels or [],
                config=prompt.config or {}
            )
            logger.info(f"Created prompt '{prompt.name}' successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create prompt '{prompt.name}': {e}")
            return False
    
    def _validate_prompt_template(self, prompt: PromptTemplate) -> bool:
        """Validate prompt template before creation."""
        if not prompt.name or not prompt.name.strip():
            logger.error("Prompt name is required")
            return False
        
        if not prompt.content or not prompt.content.strip():
            logger.error("Prompt content is required")
            return False
        
        return True
    
    def is_available(self) -> bool:
        """Check if Langfuse service is operational.
        
        Returns:
            True if service is enabled and client is initialized
        """
        return self.enabled and self.client is not None
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Langfuse service.
        
        Returns:
            Dictionary with detailed service status information
        """
        return {
            "service_name": "langfuse",
            "sdk_available": LANGFUSE_AVAILABLE,
            "enabled": self.enabled,
            "client_initialized": self.client is not None,
            "credentials_configured": self._validate_credentials(),
            "host": self.settings.langfuse_host,
            "connection_status": self._test_connection()
        }
    
    def _test_connection(self) -> str:
        """Test connection to Langfuse service."""
        if not self.is_available():
            return "unavailable"
        
        try:
            # Attempt a lightweight operation to test connectivity
            self.client.get_prompt(name="connection-test")
            return "connected"
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return f"failed: {type(e).__name__}"


# Fallback prompt templates for when Langfuse is unavailable
FALLBACK_PROMPTS = {
    "sql_system_message": """You are an expert SQL assistant for UberEats Brasil invoice data analysis.

DATA SCHEMA GUIDELINES:
- Restaurant information: vendor_name (primary field for restaurants)
- Customer information: customer_name
- Main table: ubears_invoices_extract_airflow
- Always include vendor_name when displaying restaurant data

QUERY CONSTRUCTION RULES:
1. Add WHERE clauses only when explicitly requested
2. For general queries ("show invoices"), avoid automatic date filtering
3. Include vendor_name in SELECT for restaurant-related queries
4. Use LIMIT for reasonable result sets (default: 10 for exploration)
5. Apply date filters only when user specifies time ranges

Output clean PostgreSQL SELECT statements without explanations or formatting.""",
    
    "sql_generation_template": """
Based on the database schema, convert this question to SQL:

Database Schema:
{schema}

CRITICAL RULES:
1. ALWAYS use ubears_invoices_extract_airflow table for invoice queries - this is the main table with all data
2. Restaurant names are in vendor_name field (NOT customer_name)
3. ALWAYS include vendor_name when showing restaurant information
4. ONLY add WHERE conditions when user explicitly requests filtering
5. For general queries, do NOT add automatic date filters

MANDATORY Table Selection:
- For ANY invoice query → USE ubears_invoices_extract_airflow table
- For vendor/restaurant queries → USE ubears_invoices_extract_airflow.vendor_name (REQUIRED)
- For amount queries → USE ubears_invoices_extract_airflow.total_amount, subtotal_amount, tax_amount, etc.
- For customer queries → USE ubears_invoices_extract_airflow.customer_name, customer_address, etc.

Available Amount Fields:
- total_amount: Total invoice amount
- subtotal_amount: Amount before tax
- tax_amount: Tax amount
- discount_amount: Discount applied
- shipping_amount: Shipping cost
- amount_paid: Amount already paid
- amount_due: Outstanding amount
- tip_amount: Tip amount

Available Date Fields:
- invoice_date: Date of the invoice
- due_date: Payment due date
- issue_date: Issue date
- created_at: Record creation timestamp
- extracted_at: Data extraction timestamp
- updated_at: Record update timestamp

Rules:
1. Only generate SELECT statements
2. Use proper SQL syntax for PostgreSQL  
3. Return only the SQL query, no explanations
4. ALWAYS use ubears_invoices_extract_airflow as the table name
5. Use appropriate date fields based on the context of the question

Question: {question}

SQL Query:
"""
}


def get_fallback_prompt(
    name: str, 
    variables: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Retrieve and format fallback prompt template.
    
    Args:
        name: Prompt template identifier
        variables: Template variables for formatting
        
    Returns:
        Formatted prompt string or None if template not found
        
    Raises:
        KeyError: If required template variables are missing
    """
    template = FALLBACK_PROMPTS.get(name)
    if not template:
        logger.warning(f"Fallback prompt '{name}' not found")
        return None
    
    if not variables:
        return template
    
    try:
        return template.format(**variables)
    except KeyError as e:
        logger.error(f"Missing required variable {e} for prompt '{name}'")
        raise
    except Exception as e:
        logger.error(f"Template formatting failed for '{name}': {e}")
        return None