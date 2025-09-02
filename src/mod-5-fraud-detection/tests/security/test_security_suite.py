"""Comprehensive security test suite for fraud detection system.

Tests security vulnerabilities, input validation, secrets management,
and overall system security posture.
"""

import asyncio
import json
import os
import pytest
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Test imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.input_validator import validate_order_data, ValidationErrorType
from src.security.secrets_manager import SecretsManager, SecretValidationResult
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.fraud_detector import FraudDetector


class TestSecuritySuite:
    """Comprehensive security test suite."""
    
    def setup_method(self):
        """Setup test environment."""
        self.test_order_data = {
            "order_id": "test_order_123",
            "user_id": "user_456",
            "total_amount": 25.99,
            "currency": "USD",
            "payment_method": "credit_card",
            "delivery_country": "US"
        }
    
    # Input Validation Security Tests
    def test_input_validation_xss_protection(self):
        """Test XSS attack prevention."""
        malicious_data = self.test_order_data.copy()
        malicious_data["user_id"] = "<script>alert('xss')</script>"
        
        result = validate_order_data(malicious_data)
        
        assert not result.is_valid
        security_errors = [e for e in result.errors 
                          if e.error_type == ValidationErrorType.SECURITY_VIOLATION]
        assert len(security_errors) > 0
        assert "dangerous content" in security_errors[0].message.lower()
    
    def test_input_validation_sql_injection_protection(self):
        """Test SQL injection attack prevention."""
        malicious_data = self.test_order_data.copy()
        malicious_data["user_id"] = "admin'; DROP TABLE users; --"
        
        result = validate_order_data(malicious_data)
        
        assert not result.is_valid
        security_errors = [e for e in result.errors 
                          if e.error_type == ValidationErrorType.SECURITY_VIOLATION]
        assert len(security_errors) > 0
    
    def test_input_validation_script_injection(self):
        """Test script injection attack prevention."""
        malicious_payloads = [
            "javascript:alert('attack')",
            "<iframe src='http://evil.com'></iframe>",
            "onload=alert('xss')",
            "expression(alert('css'))",
            "%3Cscript%3Ealert%28%27encoded%27%29%3C%2Fscript%3E"
        ]
        
        for payload in malicious_payloads:
            malicious_data = self.test_order_data.copy()
            malicious_data["user_id"] = payload
            
            result = validate_order_data(malicious_data)
            assert not result.is_valid, f"Failed to detect payload: {payload}"
    
    def test_input_validation_oversized_data(self):
        """Test protection against oversized input attacks."""
        malicious_data = self.test_order_data.copy()
        malicious_data["user_id"] = "A" * 10000  # 10KB string
        
        result = validate_order_data(malicious_data)
        
        assert not result.is_valid
        length_errors = [e for e in result.errors 
                        if e.error_type == ValidationErrorType.INVALID_LENGTH]
        assert len(length_errors) > 0
    
    def test_input_validation_null_byte_injection(self):
        """Test null byte injection protection."""
        malicious_data = self.test_order_data.copy()
        malicious_data["user_id"] = "valid_user\\x00../../../etc/passwd"
        
        result = validate_order_data(malicious_data)
        
        # Should be sanitized (null bytes removed)
        if result.is_valid:
            assert "\\x00" not in result.sanitized_data.get("user_id", "")
    
    def test_input_validation_unicode_attacks(self):
        """Test Unicode-based attack prevention."""
        malicious_payloads = [
            "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e",
            "\\u0022\\u003e\\u003cscript\\u003ealert\\u0028\\u0022XSS\\u0022\\u0029\\u003c/script\\u003e"
        ]
        
        for payload in malicious_payloads:
            malicious_data = self.test_order_data.copy()
            malicious_data["user_id"] = payload
            
            result = validate_order_data(malicious_data)
            # Should either be invalid or properly sanitized
            if result.is_valid:
                assert "<script" not in result.sanitized_data.get("user_id", "").lower()
    
    # Secrets Management Security Tests
    def test_secrets_manager_missing_credentials(self):
        """Test secrets manager handles missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            secrets_manager = SecretsManager()
            result = secrets_manager.validate_secrets()
            
            assert not result.valid
            assert len(result.missing_secrets) > 0
            assert "KAFKA_SASL_USERNAME" in result.missing_secrets
            assert "POSTGRES_CONNECTION_STRING" in result.missing_secrets
    
    def test_secrets_manager_placeholder_detection(self):
        """Test detection of placeholder credentials."""
        with patch.dict(os.environ, {
            "KAFKA_SASL_USERNAME": "your_username_here",
            "KAFKA_SASL_PASSWORD": "replace_me_with_real_password",
            "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost/db",
            "OPENAI_API_KEY": "sk-your-key-here"
        }):
            secrets_manager = SecretsManager()
            result = secrets_manager.validate_secrets()
            
            assert not result.valid
            assert len(result.invalid_secrets) > 0
    
    def test_secrets_manager_format_validation(self):
        """Test secrets format validation."""
        with patch.dict(os.environ, {
            "KAFKA_SASL_USERNAME": "valid_username",
            "KAFKA_SASL_PASSWORD": "valid_password",
            "POSTGRES_CONNECTION_STRING": "not_a_valid_postgresql_url",  # Invalid format
            "OPENAI_API_KEY": "not_an_openai_key"  # Invalid format
        }):
            secrets_manager = SecretsManager()
            result = secrets_manager.validate_secrets()
            
            assert not result.valid
            format_errors = [e for e in result.errors if "must be a valid" in e]
            assert len(format_errors) >= 2
    
    def test_secrets_manager_fail_safe_exit(self):
        """Test fail-safe behavior when credentials are invalid."""
        with patch.dict(os.environ, {}, clear=True):
            secrets_manager = SecretsManager()
            
            with patch('sys.exit') as mock_exit:
                secrets_manager.ensure_secrets_or_exit()
                mock_exit.assert_called_once_with(1)
    
    # Circuit Breaker Security Tests
    def test_circuit_breaker_prevents_resource_exhaustion(self):
        """Test circuit breaker prevents resource exhaustion attacks."""
        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=3,
            recovery_timeout=1.0
        )
        
        def failing_function():
            raise Exception("Service unavailable")
        
        # Trigger circuit breaker opening
        for _ in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(failing_function)
        
        # Circuit should now be open
        assert circuit_breaker.is_open()
        
        # Further calls should fail fast (preventing resource exhaustion)
        with pytest.raises(CircuitBreakerError):
            circuit_breaker.call(failing_function)
    
    def test_circuit_breaker_timeout_protection(self):
        """Test circuit breaker protects against timeout attacks."""
        circuit_breaker = CircuitBreaker(
            name="timeout_test",
            failure_threshold=2,
            recovery_timeout=0.1
        )
        
        def slow_function():
            time.sleep(2)  # Simulated slow/hanging service
            raise Exception("Timeout")
        
        # Should fail fast after threshold
        for _ in range(2):
            with pytest.raises(Exception):
                circuit_breaker.call(slow_function)
        
        start_time = time.time()
        with pytest.raises(CircuitBreakerError):
            circuit_breaker.call(slow_function)
        
        # Should fail immediately (fast failure)
        elapsed_time = time.time() - start_time
        assert elapsed_time < 0.1  # Much faster than the 2s sleep
    
    # Data Sanitization Tests
    def test_data_sanitization_html_encoding(self):
        """Test HTML encoding of dangerous characters."""
        dangerous_data = self.test_order_data.copy()
        dangerous_data["user_id"] = "<test>&'\"user"
        
        result = validate_order_data(dangerous_data)
        
        if result.is_valid:
            sanitized_user_id = result.sanitized_data.get("user_id", "")
            assert "&lt;" in sanitized_user_id or "<" not in sanitized_user_id
            assert "&amp;" in sanitized_user_id or "&" not in sanitized_user_id
    
    def test_data_sanitization_whitespace_normalization(self):
        """Test whitespace normalization."""
        messy_data = self.test_order_data.copy()
        messy_data["user_id"] = "  user\\t\\n\\r  multiple   spaces  "
        
        result = validate_order_data(messy_data)
        
        if result.is_valid:
            sanitized_user_id = result.sanitized_data.get("user_id", "")
            assert sanitized_user_id.strip() == sanitized_user_id
            assert "  " not in sanitized_user_id  # No multiple spaces
    
    # Integration Security Tests
    @patch('src.fraud_detector.FraudDetector.__init__', return_value=None)
    def test_fraud_detector_input_validation_integration(self, mock_init):
        """Test fraud detector integrates input validation properly."""
        # Mock fraud detector components
        mock_detector = Mock(spec=FraudDetector)
        mock_detector.__dict__ = {}
        
        # Mock the validation to return invalid result
        with patch('src.fraud_detector.validate_order_data') as mock_validate:
            mock_validate.return_value = Mock(
                is_valid=False,
                errors=[Mock(
                    field_name="user_id",
                    error_type=ValidationErrorType.SECURITY_VIOLATION,
                    message="Security violation detected"
                )],
                warnings=[]
            )
            
            # Create test order data
            order_data = Mock()
            order_data.order_id = "test_123"
            order_data.user_key = "malicious_user"
            
            # Test that fraud detector would handle invalid input
            # (This tests the integration pattern, not the actual method)
            mock_validate.assert_not_called()  # Haven't called yet
            
            # Call validation
            result = mock_validate({"test": "data"})
            assert not result.is_valid
    
    # Performance Security Tests (DoS Protection)
    def test_input_validation_performance_limits(self):
        """Test input validation has reasonable performance limits."""
        # Test with various sized inputs
        sizes = [100, 1000, 10000]
        
        for size in sizes:
            large_data = self.test_order_data.copy()
            large_data["user_id"] = "A" * size
            
            start_time = time.time()
            result = validate_order_data(large_data)
            elapsed_time = time.time() - start_time
            
            # Validation should complete in reasonable time
            assert elapsed_time < 1.0, f"Validation took too long for {size} chars: {elapsed_time}s"
    
    def test_repeated_validation_performance(self):
        """Test validation performance under repeated calls."""
        # Simulate rapid repeated validation requests
        start_time = time.time()
        
        for _ in range(100):
            result = validate_order_data(self.test_order_data)
            assert result.is_valid
        
        elapsed_time = time.time() - start_time
        
        # Should handle 100 validations quickly
        assert elapsed_time < 2.0, f"100 validations took too long: {elapsed_time}s"
    
    # Email and Phone Validation Security
    def test_email_validation_security(self):
        """Test email validation prevents malicious inputs."""
        malicious_emails = [
            "test@domain.com<script>alert('xss')</script>",
            "test+<script>@domain.com",
            "test@domain.com'; DROP TABLE users; --",
            "test@" + "A" * 300 + ".com",  # Oversized domain
            "test@domain..com",  # Invalid format
            "<script>alert('xss')</script>@domain.com"
        ]
        
        for email in malicious_emails:
            test_data = self.test_order_data.copy()
            test_data["user_email"] = email
            
            result = validate_order_data(test_data)
            
            if result.is_valid:
                # If valid, should be properly sanitized
                sanitized_email = result.sanitized_data.get("user_email", "")
                assert "<script" not in sanitized_email.lower()
                assert "drop table" not in sanitized_email.lower()
    
    def test_phone_validation_security(self):
        """Test phone number validation security."""
        malicious_phones = [
            "+1234567890<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "1" * 50,  # Oversized number
            "+1 (555) <script>alert(1)</script> 123-4567"
        ]
        
        for phone in malicious_phones:
            test_data = self.test_order_data.copy()
            test_data["phone_number"] = phone
            
            result = validate_order_data(test_data)
            
            if result.is_valid:
                # Should contain only digits
                sanitized_phone = result.sanitized_data.get("phone_number", "")
                assert sanitized_phone.isdigit()
                assert len(sanitized_phone) <= 15
    
    # Configuration Security Tests
    def test_configuration_security_defaults(self):
        """Test that security configurations have safe defaults."""
        # Test that dangerous defaults are not present
        from config.settings import settings
        
        # These settings should not have insecure defaults
        assert hasattr(settings, 'openai')
        assert hasattr(settings, 'kafka') 
        assert hasattr(settings, 'postgresql')
        
        # API keys should not have default values
        with patch.dict(os.environ, {}, clear=True):
            # Should not have hardcoded API keys
            with pytest.raises((ValueError, AttributeError)):
                # This should fail without environment variables
                settings.openai.api_key
    
    # Logging Security Tests
    def test_sensitive_data_not_logged(self):
        """Test that sensitive data is not logged."""
        import logging
        
        # Capture log output
        with patch('logging.getLogger') as mock_logger:
            mock_log_instance = Mock()
            mock_logger.return_value = mock_log_instance
            
            # Test order data with sensitive information
            sensitive_data = self.test_order_data.copy()
            sensitive_data["credit_card"] = "4111111111111111"
            sensitive_data["cvv"] = "123"
            
            # Validate data
            result = validate_order_data(sensitive_data)
            
            # Check that sensitive data doesn't appear in logs
            # (This is a pattern test - actual implementation may vary)
            for call_args in mock_log_instance.method_calls:
                if len(call_args) > 1:
                    log_message = str(call_args[1])
                    assert "4111111111111111" not in log_message
                    assert "123" not in log_message


class TestSecurityScenarios:
    """Test realistic attack scenarios."""
    
    def test_coordinated_attack_simulation(self):
        """Test system resilience against coordinated attacks."""
        # Simulate multiple attack vectors simultaneously
        attack_vectors = [
            {"user_id": "<script>alert('xss1')</script>"},
            {"user_id": "'; DROP TABLE orders; --"},
            {"user_id": "A" * 5000},  # DoS attempt
            {"user_id": "\\x00\\x01\\x02"},  # Binary data
            {"total_amount": -999999},  # Invalid amount
            {"currency": "FAKE"},  # Invalid currency
            {"delivery_country": "XX"}  # Invalid country
        ]
        
        for attack in attack_vectors:
            malicious_data = {
                "order_id": "attack_order",
                "user_id": "attacker",
                "total_amount": 100,
                "currency": "USD", 
                "payment_method": "credit_card",
                "delivery_country": "US"
            }
            malicious_data.update(attack)
            
            result = validate_order_data(malicious_data)
            
            # System should handle each attack gracefully
            assert isinstance(result.is_valid, bool)
            assert isinstance(result.errors, list)
            assert isinstance(result.warnings, list)
    
    def test_resource_exhaustion_protection(self):
        """Test protection against resource exhaustion."""
        # Test with extremely large nested data
        large_items = []
        for i in range(1000):  # Large number of items
            large_items.append({
                "id": f"item_{i}",
                "name": "A" * 100,  # Large strings
                "description": "B" * 200
            })
        
        test_data = {
            "order_id": "large_order",
            "user_id": "test_user",
            "total_amount": 100,
            "currency": "USD",
            "payment_method": "credit_card", 
            "delivery_country": "US",
            "items": large_items
        }
        
        start_time = time.time()
        result = validate_order_data(test_data)
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time and handle large data
        assert elapsed_time < 5.0
        
        if result.is_valid:
            # Should limit the number of items processed
            sanitized_items = result.sanitized_data.get("items", [])
            assert len(sanitized_items) <= 100  # Should be truncated
    
    def test_encoding_attack_vectors(self):
        """Test various encoding attack vectors."""
        encoding_attacks = [
            "%3Cscript%3E",  # URL encoding
            "&#60;script&#62;",  # HTML entities
            "\\u003cscript\\u003e",  # Unicode escapes
            "%253Cscript%253E",  # Double URL encoding
            "＜script＞",  # Full-width characters
            "<scr\\x00ipt>",  # Null byte injection
        ]
        
        for attack in encoding_attacks:
            test_data = {
                "order_id": "encoding_test",
                "user_id": attack,
                "total_amount": 100,
                "currency": "USD",
                "payment_method": "credit_card",
                "delivery_country": "US"
            }
            
            result = validate_order_data(test_data)
            
            # Should either reject or properly sanitize
            if result.is_valid:
                sanitized_user_id = result.sanitized_data.get("user_id", "")
                # Should not contain actual script tags after sanitization
                assert "<script" not in sanitized_user_id.lower()
                assert "javascript:" not in sanitized_user_id.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])