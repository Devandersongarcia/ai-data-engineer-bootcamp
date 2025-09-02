"""Secure secrets management system for UberEats Fraud Detection.

This module provides secure credential management with validation,
encryption options, and fail-safe mechanisms to prevent credential exposure.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SecretValidationResult:
    """Result of secret validation check.
    
    Attributes:
        valid: Whether all required secrets are valid
        missing_secrets: List of missing required secret keys
        invalid_secrets: List of invalid secret keys
        errors: List of validation error messages
    """
    valid: bool
    missing_secrets: list[str]
    invalid_secrets: list[str]
    errors: list[str]


class SecretsManager:
    """Secure secrets management with validation and fail-safe mechanisms."""
    
    # Critical environment variables that MUST be present
    REQUIRED_SECRETS = {
        'KAFKA_SASL_USERNAME': 'Kafka SASL username for Confluent Cloud',
        'KAFKA_SASL_PASSWORD': 'Kafka SASL password for Confluent Cloud',
        'POSTGRES_CONNECTION_STRING': 'PostgreSQL connection string',
        'OPENAI_API_KEY': 'OpenAI API key for LLM operations'
    }
    
    # Optional secrets with descriptions
    OPTIONAL_SECRETS = {
        'QDRANT_API_KEY': 'Qdrant vector database API key',
        'REDIS_PASSWORD': 'Redis password if authentication is enabled',
        'LANGFUSE_PUBLIC_KEY': 'Langfuse public key for LLM observability',
        'LANGFUSE_SECRET_KEY': 'Langfuse secret key for LLM observability'
    }
    
    def __init__(self):
        """Initialize the secrets manager."""
        self.validation_result: Optional[SecretValidationResult] = None
    
    def validate_secrets(self) -> SecretValidationResult:
        """Validate all required secrets are present and valid.
        
        Returns:
            SecretValidationResult with validation status and details
        """
        missing_secrets = []
        invalid_secrets = []
        errors = []
        
        # Check required secrets
        for secret_key, description in self.REQUIRED_SECRETS.items():
            value = os.getenv(secret_key)
            
            if not value:
                missing_secrets.append(secret_key)
                errors.append(f"Missing required secret: {secret_key} ({description})")
            elif value.strip() == "":
                invalid_secrets.append(secret_key)
                errors.append(f"Empty value for required secret: {secret_key}")
            elif self._is_placeholder_value(value):
                invalid_secrets.append(secret_key)
                errors.append(f"Placeholder value detected for: {secret_key}")
        
        # Validate specific secret formats
        self._validate_secret_formats(errors, invalid_secrets)
        
        is_valid = len(missing_secrets) == 0 and len(invalid_secrets) == 0
        
        result = SecretValidationResult(
            valid=is_valid,
            missing_secrets=missing_secrets,
            invalid_secrets=invalid_secrets,
            errors=errors
        )
        
        self.validation_result = result
        return result
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if a value is a placeholder/template value."""
        placeholders = [
            'your_', 'placeholder', 'template', 'example',
            'change_me', 'replace_me', 'todo', 'fixme'
        ]
        value_lower = value.lower()
        return any(placeholder in value_lower for placeholder in placeholders)
    
    def _validate_secret_formats(self, errors: list[str], invalid_secrets: list[str]) -> None:
        """Validate specific secret formats."""
        # Validate PostgreSQL connection string
        postgres_conn = os.getenv('POSTGRES_CONNECTION_STRING', '').strip()
        if postgres_conn and not postgres_conn.startswith('postgresql://'):
            errors.append("POSTGRES_CONNECTION_STRING must be a valid PostgreSQL URL")
            invalid_secrets.append('POSTGRES_CONNECTION_STRING')
        
        # Validate OpenAI API key format
        openai_key = os.getenv('OPENAI_API_KEY', '').strip()
        if openai_key and not (openai_key.startswith('sk-') and len(openai_key) > 20):
            errors.append("OPENAI_API_KEY must be a valid OpenAI API key starting with 'sk-'")
            invalid_secrets.append('OPENAI_API_KEY')
    
    def ensure_secrets_or_exit(self) -> None:
        """Validate secrets and exit if any are missing or invalid.
        
        This is a fail-safe mechanism to prevent the application from starting
        with missing or invalid credentials.
        """
        result = self.validate_secrets()
        
        if not result.valid:
            print("🚨 CRITICAL SECURITY ERROR: Missing or invalid credentials!")
            print("=" * 60)
            
            if result.missing_secrets:
                print("❌ Missing Required Environment Variables:")
                for secret in result.missing_secrets:
                    description = self.REQUIRED_SECRETS.get(secret, "Required credential")
                    print(f"   • {secret}: {description}")
            
            if result.invalid_secrets:
                print("\n❌ Invalid Environment Variables:")
                for secret in result.invalid_secrets:
                    print(f"   • {secret}: Invalid format or placeholder value")
            
            print("\n🔧 To fix this:")
            print("1. Copy .env.example to .env")
            print("2. Fill in your actual credentials")
            print("3. Ensure no placeholder values remain")
            
            print("\n📋 Example .env setup:")
            print("KAFKA_SASL_USERNAME=your_actual_kafka_username")
            print("KAFKA_SASL_PASSWORD=your_actual_kafka_password")
            print("POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:port/db")
            print("OPENAI_API_KEY=sk-proj-your_actual_api_key")
            
            print("\n🔒 Security Note: Never commit .env files to version control!")
            print("=" * 60)
            
            sys.exit(1)
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Safely get a secret value.
        
        Args:
            key: Environment variable key
            default: Default value if not found
            
        Returns:
            Secret value or default
        """
        value = os.getenv(key, default)
        return value.strip() if value else value
    
    def get_required_secret(self, key: str) -> str:
        """Get a required secret value.
        
        Args:
            key: Environment variable key
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret is missing or invalid
        """
        value = self.get_secret(key)
        if not value:
            raise ValueError(f"Required secret {key} is missing or empty")
        return value
    
    def print_validation_summary(self) -> None:
        """Print a summary of secret validation results."""
        if not self.validation_result:
            self.validate_secrets()
        
        result = self.validation_result
        
        if result.valid:
            print("✅ All required secrets are properly configured")
            return
        
        print("⚠️  Secret Validation Issues:")
        for error in result.errors:
            print(f"   • {error}")


# Global secrets manager instance
secrets_manager = SecretsManager()


def ensure_secure_startup() -> None:
    """Ensure secure application startup with proper credential validation.
    
    Call this function at the start of your application to validate
    all credentials before any processing begins.
    """
    secrets_manager.ensure_secrets_or_exit()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret value."""
    return secrets_manager.get_secret(key, default)


def get_required_secret(key: str) -> str:
    """Convenience function to get a required secret value."""
    return secrets_manager.get_required_secret(key)