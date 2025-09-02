"""Comprehensive input validation and sanitization for fraud detection system.

Provides secure validation for all external inputs including order data,
user inputs, and API parameters to prevent injection attacks and data corruption.
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationErrorType(Enum):
    """Types of validation errors."""
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    INVALID_LENGTH = "invalid_length"
    SECURITY_VIOLATION = "security_violation"
    INVALID_TYPE = "invalid_type"


@dataclass
class ValidationError:
    """Represents a validation error."""
    field_name: str
    error_type: ValidationErrorType
    message: str
    provided_value: Any = None


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_data: Dict[str, Any]
    errors: List[ValidationError]
    warnings: List[str]


class InputValidator:
    """Comprehensive input validator with security-focused sanitization."""
    
    # Security patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript\s*:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers
        r'<iframe[^>]*>.*?</iframe>',  # Iframes
        r'<object[^>]*>.*?</object>',  # Objects
        r'<embed[^>]*>.*?</embed>',  # Embeds
        r'<link[^>]*>',  # Link tags
        r'<meta[^>]*>',  # Meta tags
        r'expression\s*\(',  # CSS expressions
        r'url\s*\(',  # URL functions in CSS
        r'@import',  # CSS imports
        r'\\x[0-9a-fA-F]{2}',  # Hex encoding
        r'%[0-9a-fA-F]{2}',  # URL encoding of control chars
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b',
        r'--\s*$',  # SQL comments
        r'/\*.*?\*/',  # SQL block comments
        r"'(\s*(or|and)\s*'.*?'|\s*(or|and)\s*\d+\s*=\s*\d+)",  # Classic SQLi
        r'\b(or|and)\s+\d+\s*=\s*\d+',  # Boolean-based SQLi
    ]
    
    # Valid country codes (ISO 3166-1 alpha-2)
    VALID_COUNTRY_CODES = {
        'US', 'CA', 'GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'CH',
        'AT', 'SE', 'NO', 'DK', 'FI', 'IE', 'PT', 'GR', 'PL', 'CZ',
        'AU', 'NZ', 'JP', 'SG', 'HK', 'KR', 'TW', 'IN', 'BR', 'MX'
    }
    
    # Valid currency codes (ISO 4217)
    VALID_CURRENCIES = {
        'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY',
        'SEK', 'NZD', 'NOK', 'DKK', 'PLN', 'CZK', 'HKD', 'SGD',
        'INR', 'BRL', 'MXN', 'KRW', 'TWD'
    }
    
    def __init__(self):
        """Initialize input validator."""
        self.compiled_dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in self.DANGEROUS_PATTERNS
        ]
        self.compiled_sql_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SQL_INJECTION_PATTERNS
        ]
    
    def validate_order_data(self, order_data: Dict[str, Any]) -> ValidationResult:
        """Validate and sanitize order data for fraud detection.
        
        Args:
            order_data: Raw order data dictionary
            
        Returns:
            ValidationResult with validation status and sanitized data
        """
        errors = []
        warnings = []
        sanitized_data = {}
        
        # Required fields for fraud detection
        required_fields = {
            'order_id': str,
            'user_id': str,
            'total_amount': (int, float, str),
            'currency': str,
            'payment_method': str,
            'delivery_country': str,
        }
        
        # Validate required fields
        for field_name, expected_type in required_fields.items():
            if field_name not in order_data:
                errors.append(ValidationError(
                    field_name=field_name,
                    error_type=ValidationErrorType.REQUIRED_FIELD_MISSING,
                    message=f"Required field '{field_name}' is missing"
                ))
                continue
            
            value = order_data[field_name]
            
            if not isinstance(value, expected_type):
                errors.append(ValidationError(
                    field_name=field_name,
                    error_type=ValidationErrorType.INVALID_TYPE,
                    message=f"Field '{field_name}' must be of type {expected_type}",
                    provided_value=type(value).__name__
                ))
                continue
            
            # Field-specific validation
            sanitized_value = self._validate_specific_field(field_name, value, errors, warnings)
            if sanitized_value is not None:
                sanitized_data[field_name] = sanitized_value
        
        # Optional fields validation
        optional_fields = {
            'user_email': str,
            'phone_number': str,
            'delivery_address': dict,
            'items': list,
            'promotion_codes': list,
            'user_agent': str,
            'ip_address': str,
            'session_id': str
        }
        
        for field_name, expected_type in optional_fields.items():
            if field_name in order_data:
                value = order_data[field_name]
                if isinstance(value, expected_type):
                    sanitized_value = self._validate_specific_field(field_name, value, errors, warnings)
                    if sanitized_value is not None:
                        sanitized_data[field_name] = sanitized_value
                else:
                    warnings.append(f"Optional field '{field_name}' has incorrect type, skipping")
        
        # Add validation timestamp
        sanitized_data['validation_timestamp'] = datetime.now().isoformat()
        sanitized_data['validation_version'] = '1.0'
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_data=sanitized_data,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_specific_field(
        self, 
        field_name: str, 
        value: Any, 
        errors: List[ValidationError], 
        warnings: List[str]
    ) -> Optional[Any]:
        """Validate specific field based on field name and type.
        
        Args:
            field_name: Name of the field
            value: Field value
            errors: List to append errors to
            warnings: List to append warnings to
            
        Returns:
            Sanitized value or None if validation fails
        """
        try:
            if field_name == 'order_id':
                return self._validate_order_id(value, errors)
            elif field_name == 'user_id':
                return self._validate_user_id(value, errors)
            elif field_name == 'total_amount':
                return self._validate_amount(value, errors)
            elif field_name == 'currency':
                return self._validate_currency(value, errors)
            elif field_name == 'payment_method':
                return self._validate_payment_method(value, errors)
            elif field_name == 'delivery_country':
                return self._validate_country_code(value, errors)
            elif field_name == 'user_email':
                return self._validate_email(value, errors)
            elif field_name == 'phone_number':
                return self._validate_phone_number(value, errors)
            elif field_name == 'delivery_address':
                return self._validate_address(value, errors, warnings)
            elif field_name == 'items':
                return self._validate_items(value, errors, warnings)
            elif field_name == 'ip_address':
                return self._validate_ip_address(value, errors)
            elif field_name in ['user_agent', 'session_id']:
                return self._validate_and_sanitize_string(value, field_name, 1000, errors)
            else:
                # Generic string validation for unknown fields
                if isinstance(value, str):
                    return self._validate_and_sanitize_string(value, field_name, 500, errors)
                return value
                
        except Exception as e:
            logger.error(f"Error validating field '{field_name}': {e}")
            errors.append(ValidationError(
                field_name=field_name,
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=f"Validation error for field '{field_name}': {str(e)}",
                provided_value=value
            ))
            return None
    
    def _validate_order_id(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate order ID format."""
        sanitized = self._sanitize_string(str(value))
        
        # Order ID should be alphanumeric with possible hyphens/underscores
        if not re.match(r'^[a-zA-Z0-9_-]{1,50}$', sanitized):
            errors.append(ValidationError(
                field_name='order_id',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Order ID must be 1-50 characters, alphanumeric with hyphens/underscores only",
                provided_value=value
            ))
            return None
        
        return sanitized
    
    def _validate_user_id(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate user ID format."""
        sanitized = self._sanitize_string(str(value))
        
        # User ID should be alphanumeric
        if not re.match(r'^[a-zA-Z0-9_-]{1,100}$', sanitized):
            errors.append(ValidationError(
                field_name='user_id',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="User ID must be 1-100 characters, alphanumeric with hyphens/underscores only",
                provided_value=value
            ))
            return None
        
        return sanitized
    
    def _validate_amount(self, value: Union[int, float, str], errors: List[ValidationError]) -> Optional[Decimal]:
        """Validate monetary amount."""
        try:
            # Convert to Decimal for precise monetary calculations
            if isinstance(value, str):
                # Remove common formatting
                cleaned = re.sub(r'[,$\s]', '', value)
                amount = Decimal(cleaned)
            else:
                amount = Decimal(str(value))
            
            # Reasonable bounds for order amounts
            if amount < 0:
                errors.append(ValidationError(
                    field_name='total_amount',
                    error_type=ValidationErrorType.OUT_OF_RANGE,
                    message="Amount cannot be negative",
                    provided_value=value
                ))
                return None
            
            if amount > Decimal('100000'):  # $100,000 max
                errors.append(ValidationError(
                    field_name='total_amount',
                    error_type=ValidationErrorType.OUT_OF_RANGE,
                    message="Amount exceeds maximum allowed ($100,000)",
                    provided_value=value
                ))
                return None
            
            # Round to 2 decimal places for currency
            return amount.quantize(Decimal('0.01'))
            
        except (InvalidOperation, ValueError, TypeError):
            errors.append(ValidationError(
                field_name='total_amount',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Amount must be a valid number",
                provided_value=value
            ))
            return None
    
    def _validate_currency(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate currency code."""
        sanitized = str(value).upper().strip()
        
        if sanitized not in self.VALID_CURRENCIES:
            errors.append(ValidationError(
                field_name='currency',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=f"Invalid currency code. Must be one of: {', '.join(sorted(self.VALID_CURRENCIES))}",
                provided_value=value
            ))
            return None
        
        return sanitized
    
    def _validate_payment_method(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate payment method."""
        sanitized = self._sanitize_string(str(value))
        
        valid_methods = {
            'credit_card', 'debit_card', 'paypal', 'apple_pay', 'google_pay',
            'bank_transfer', 'cryptocurrency', 'gift_card', 'cash'
        }
        
        normalized = sanitized.lower().replace(' ', '_').replace('-', '_')
        
        if normalized not in valid_methods:
            errors.append(ValidationError(
                field_name='payment_method',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message=f"Invalid payment method. Must be one of: {', '.join(valid_methods)}",
                provided_value=value
            ))
            return None
        
        return normalized
    
    def _validate_country_code(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate country code."""
        sanitized = str(value).upper().strip()
        
        if sanitized not in self.VALID_COUNTRY_CODES:
            errors.append(ValidationError(
                field_name='delivery_country',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Invalid country code. Must be valid ISO 3166-1 alpha-2 code",
                provided_value=value
            ))
            return None
        
        return sanitized
    
    def _validate_email(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate email address."""
        sanitized = self._sanitize_string(str(value))
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, sanitized):
            errors.append(ValidationError(
                field_name='user_email',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Invalid email format",
                provided_value=value
            ))
            return None
        
        if len(sanitized) > 254:  # RFC 5321 limit
            errors.append(ValidationError(
                field_name='user_email',
                error_type=ValidationErrorType.INVALID_LENGTH,
                message="Email address too long (max 254 characters)",
                provided_value=value
            ))
            return None
        
        return sanitized.lower()
    
    def _validate_phone_number(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate phone number."""
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'[^\d]', '', str(value))
        
        # Basic phone number validation (7-15 digits)
        if len(digits_only) < 7 or len(digits_only) > 15:
            errors.append(ValidationError(
                field_name='phone_number',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Phone number must be 7-15 digits",
                provided_value=value
            ))
            return None
        
        return digits_only
    
    def _validate_ip_address(self, value: str, errors: List[ValidationError]) -> Optional[str]:
        """Validate IP address."""
        sanitized = str(value).strip()
        
        # Basic IPv4 validation
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        # Basic IPv6 validation (simplified)
        ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        
        if not (re.match(ipv4_pattern, sanitized) or re.match(ipv6_pattern, sanitized)):
            errors.append(ValidationError(
                field_name='ip_address',
                error_type=ValidationErrorType.INVALID_FORMAT,
                message="Invalid IP address format",
                provided_value=value
            ))
            return None
        
        return sanitized
    
    def _validate_address(self, value: dict, errors: List[ValidationError], warnings: List[str]) -> Optional[dict]:
        """Validate address dictionary."""
        if not isinstance(value, dict):
            errors.append(ValidationError(
                field_name='delivery_address',
                error_type=ValidationErrorType.INVALID_TYPE,
                message="Address must be a dictionary",
                provided_value=type(value).__name__
            ))
            return None
        
        sanitized_address = {}
        
        # Validate address fields
        address_fields = ['street', 'city', 'state', 'postal_code', 'country']
        for field in address_fields:
            if field in value:
                sanitized = self._validate_and_sanitize_string(value[field], f'address.{field}', 200, errors)
                if sanitized:
                    sanitized_address[field] = sanitized
        
        return sanitized_address if sanitized_address else None
    
    def _validate_items(self, value: list, errors: List[ValidationError], warnings: List[str]) -> Optional[list]:
        """Validate items list."""
        if not isinstance(value, list):
            errors.append(ValidationError(
                field_name='items',
                error_type=ValidationErrorType.INVALID_TYPE,
                message="Items must be a list",
                provided_value=type(value).__name__
            ))
            return None
        
        if len(value) > 100:  # Reasonable limit
            warnings.append("Order has more than 100 items, truncating for processing")
            value = value[:100]
        
        sanitized_items = []
        for i, item in enumerate(value):
            if isinstance(item, dict):
                sanitized_item = {}
                for key, val in item.items():
                    if isinstance(val, str):
                        sanitized_val = self._validate_and_sanitize_string(val, f'items[{i}].{key}', 500, errors)
                        if sanitized_val:
                            sanitized_item[key] = sanitized_val
                    else:
                        sanitized_item[key] = val
                
                if sanitized_item:
                    sanitized_items.append(sanitized_item)
        
        return sanitized_items
    
    def _validate_and_sanitize_string(
        self, 
        value: str, 
        field_name: str, 
        max_length: int, 
        errors: List[ValidationError]
    ) -> Optional[str]:
        """Validate and sanitize a string field.
        
        Args:
            value: String value to validate
            field_name: Name of the field for error reporting
            max_length: Maximum allowed length
            errors: List to append errors to
            
        Returns:
            Sanitized string or None if validation fails
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Check for security violations
        if self._contains_dangerous_content(value):
            errors.append(ValidationError(
                field_name=field_name,
                error_type=ValidationErrorType.SECURITY_VIOLATION,
                message=f"Field '{field_name}' contains potentially dangerous content",
                provided_value=value[:100]  # Truncate for logging
            ))
            return None
        
        # Sanitize the string
        sanitized = self._sanitize_string(value)
        
        # Check length after sanitization
        if len(sanitized) > max_length:
            errors.append(ValidationError(
                field_name=field_name,
                error_type=ValidationErrorType.INVALID_LENGTH,
                message=f"Field '{field_name}' exceeds maximum length of {max_length} characters",
                provided_value=len(sanitized)
            ))
            return None
        
        return sanitized
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string by removing/escaping dangerous content.
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)
        
        # HTML encode to prevent XSS
        sanitized = html.escape(value)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in ['\n', '\r', '\t'])
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def _contains_dangerous_content(self, value: str) -> bool:
        """Check if string contains dangerous patterns.
        
        Args:
            value: String to check
            
        Returns:
            True if dangerous patterns found
        """
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        # Check for dangerous patterns
        for pattern in self.compiled_dangerous_patterns:
            if pattern.search(value_lower):
                logger.warning(f"Dangerous pattern detected: {pattern.pattern}")
                return True
        
        # Check for SQL injection patterns
        for pattern in self.compiled_sql_patterns:
            if pattern.search(value_lower):
                logger.warning(f"SQL injection pattern detected: {pattern.pattern}")
                return True
        
        return False


# Global validator instance
input_validator = InputValidator()


def validate_order_data(order_data: Dict[str, Any]) -> ValidationResult:
    """Convenience function to validate order data."""
    return input_validator.validate_order_data(order_data)


def sanitize_string(value: str) -> str:
    """Convenience function to sanitize a string."""
    return input_validator._sanitize_string(value)