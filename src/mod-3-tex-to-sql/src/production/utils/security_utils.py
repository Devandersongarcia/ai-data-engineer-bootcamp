"""Security utilities for SQL validation, input sanitization, and data protection."""

import re
import hashlib
import secrets
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from config.settings import get_settings


class SecurityLevel(Enum):
    """Security validation levels."""
    STRICT = "strict"      # Only SELECT allowed, strict validation
    MODERATE = "moderate"  # SELECT + basic CTEs, moderate validation
    LENIENT = "lenient"    # More permissive for advanced queries


class SqlValidationResult:
    """Result of SQL query validation."""
    
    def __init__(self, is_valid: bool, error_message: str = None, risk_level: str = "low"):
        self.is_valid = is_valid
        self.error_message = error_message
        self.risk_level = risk_level
        self.blocked_keywords = []
        self.warnings = []
    
    def add_warning(self, warning: str):
        """Add a warning to the validation result."""
        self.warnings.append(warning)
    
    def add_blocked_keyword(self, keyword: str):
        """Add a blocked keyword to the result."""
        self.blocked_keywords.append(keyword)


def validate_sql_query(
    query: str, 
    security_level: SecurityLevel = SecurityLevel.STRICT,
    allow_cte: bool = False
) -> SqlValidationResult:
    """
    Comprehensive SQL query validation with security checks.
    
    Args:
        query: SQL query to validate
        security_level: Level of security validation
        allow_cte: Whether to allow Common Table Expressions (WITH clauses)
    
    Returns:
        SqlValidationResult with validation details
    """
    if not query or not query.strip():
        return SqlValidationResult(False, "Query cannot be empty")
    
    # Normalize query for analysis
    normalized_query = _normalize_sql_query(query)
    result = SqlValidationResult(True)
    
    # Get dangerous keywords from settings
    settings = get_settings()
    dangerous_keywords = settings.dangerous_sql_keywords
    
    # Check for dangerous keywords (whole words only to avoid false positives)
    for keyword in dangerous_keywords:
        # Use word boundary regex to match only complete keywords
        if re.search(r'\b' + re.escape(keyword.upper()) + r'\b', normalized_query):
            result.is_valid = False
            result.error_message = f"Dangerous SQL operation detected: {keyword}"
            result.risk_level = "high"
            result.add_blocked_keyword(keyword)
            return result
    
    # Check that query starts with SELECT or WITH (if CTE allowed)
    allowed_starts = ["SELECT"]
    if allow_cte:
        allowed_starts.append("WITH")
    
    if not any(normalized_query.strip().startswith(start) for start in allowed_starts):
        result.is_valid = False
        result.error_message = "Only SELECT queries are allowed"
        result.risk_level = "high"
        return result
    
    # Additional security checks based on level
    if security_level == SecurityLevel.STRICT:
        result = _strict_validation(normalized_query, result)
    elif security_level == SecurityLevel.MODERATE:
        result = _moderate_validation(normalized_query, result)
    
    # Check for suspicious patterns
    result = _check_suspicious_patterns(normalized_query, result)
    
    return result


def _normalize_sql_query(query: str) -> str:
    """Normalize SQL query for consistent analysis."""
    # Remove comments
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query.strip())
    
    return query.upper()


def _strict_validation(query: str, result: SqlValidationResult) -> SqlValidationResult:
    """Apply strict security validation rules."""
    # Check for function calls that might be risky
    risky_functions = [
        'EXEC', 'EXECUTE', 'SP_', 'XP_', 'OPENROWSET', 'OPENDATASOURCE',
        'BULK', 'LOADXML', 'OPENXML'
    ]
    
    for func in risky_functions:
        if func in query:
            result.add_warning(f"Potentially risky function detected: {func}")
            result.risk_level = "medium"
    
    # Limit complexity - no nested subqueries beyond 2 levels
    subquery_count = query.count('(SELECT')
    if subquery_count > 2:
        result.add_warning(f"Complex nested queries detected ({subquery_count} levels)")
        result.risk_level = "medium"
    
    return result


def _moderate_validation(query: str, result: SqlValidationResult) -> SqlValidationResult:
    """Apply moderate security validation rules."""
    # Allow more flexibility but still check for obvious issues
    if 'UNION' in query and 'ALL' not in query:
        result.add_warning("UNION without ALL detected - potential performance impact")
    
    return result


def _check_suspicious_patterns(query: str, result: SqlValidationResult) -> SqlValidationResult:
    """Check for suspicious SQL patterns."""
    suspicious_patterns = [
        (r"'\s*OR\s+'", "Potential SQL injection pattern"),
        (r";\s*(DROP|DELETE|UPDATE)", "Multiple statements with dangerous operations"),
        (r"WAITFOR\s+DELAY", "Time-based attack pattern"),
        (r"@@\w+", "System variable access"),
    ]
    
    for pattern, description in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            result.add_warning(description)
            result.risk_level = "high" if result.risk_level != "high" else result.risk_level
    
    return result


def sanitize_input(user_input: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing/escaping dangerous characters.
    
    Args:
        user_input: Raw user input
        max_length: Maximum allowed length
    
    Returns:
        Sanitized input string
    """
    if not user_input:
        return ""
    
    # Truncate if too long
    if len(user_input) > max_length:
        user_input = user_input[:max_length]
    
    # Remove null bytes and control characters
    user_input = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_input)
    
    # Escape single quotes for SQL safety (double them)
    user_input = user_input.replace("'", "''")
    
    # Remove obvious script injection attempts
    script_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
    ]
    
    for pattern in script_patterns:
        user_input = re.sub(pattern, '', user_input, flags=re.IGNORECASE | re.DOTALL)
    
    return user_input.strip()


def mask_sensitive_data(data: str, patterns: List[str] = None) -> str:
    """
    Mask sensitive data in strings for logging and display.
    
    Args:
        data: String containing potentially sensitive data
        patterns: Custom regex patterns to mask
    
    Returns:
        String with sensitive data masked
    """
    if not data:
        return data
    
    if patterns is None:
        patterns = [
            # API Keys
            (r'(api[_\-]?key["\s]*[:=]["\s]*)([a-zA-Z0-9\-_]{10,})', r'\1***MASKED***'),
            # Passwords
            (r'(password["\s]*[:=]["\s]*)([^\s"]{6,})', r'\1***MASKED***'),
            # Tokens
            (r'(token["\s]*[:=]["\s]*)([a-zA-Z0-9\-_\.]{10,})', r'\1***MASKED***'),
            # Database URLs with passwords
            (r'(postgresql://[^:]+:)([^@]+)(@)', r'\1***MASKED***\3'),
            # Email addresses (partial masking)
            (r'([a-zA-Z0-9._%+-]+)(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'***MASKED***\2'),
        ]
    
    masked_data = data
    for pattern, replacement in patterns:
        masked_data = re.sub(pattern, replacement, masked_data, flags=re.IGNORECASE)
    
    return masked_data


def generate_session_id() -> str:
    """Generate a secure session ID."""
    return secrets.token_urlsafe(32)


def hash_query_for_caching(query: str, params: Dict[str, Any] = None) -> str:
    """
    Generate a secure hash for query caching.
    
    Args:
        query: SQL query string
        params: Query parameters
    
    Returns:
        SHA-256 hash of the query and parameters
    """
    hasher = hashlib.sha256()
    
    # Add query
    hasher.update(query.encode('utf-8'))
    
    # Add parameters if provided
    if params:
        param_str = str(sorted(params.items()))
        hasher.update(param_str.encode('utf-8'))
    
    return hasher.hexdigest()


def validate_database_connection_string(connection_string: str) -> Tuple[bool, str]:
    """
    Validate database connection string format and security.
    
    Args:
        connection_string: Database connection string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not connection_string:
        return False, "Connection string cannot be empty"
    
    # Check for basic format (postgresql://)
    if not re.match(r'^postgresql://', connection_string, re.IGNORECASE):
        return False, "Only PostgreSQL connections are supported"
    
    # Check for suspicious elements
    suspicious_patterns = [
        r'localhost',  # Warn about localhost in production
        r'127\.0\.0\.1',  # Warn about local IP
        r'admin',  # Warn about admin user
        r'root',   # Warn about root user
    ]
    
    warnings = []
    for pattern in suspicious_patterns:
        if re.search(pattern, connection_string, re.IGNORECASE):
            if 'localhost' in pattern or '127.0.0.1' in pattern:
                warnings.append("Using local database - ensure this is intended for production")
            elif 'admin' in pattern or 'root' in pattern:
                warnings.append("Using privileged database user - consider using limited permissions")
    
    if warnings:
        return True, f"Valid but with warnings: {'; '.join(warnings)}"
    
    return True, "Valid connection string"


class InputValidator:
    """Reusable input validator with configurable rules."""
    
    def __init__(self):
        self.rules = []
    
    def add_rule(self, name: str, pattern: str, error_message: str):
        """Add a validation rule."""
        self.rules.append({
            'name': name,
            'pattern': re.compile(pattern, re.IGNORECASE),
            'error_message': error_message
        })
    
    def validate(self, input_string: str) -> Tuple[bool, List[str]]:
        """
        Validate input against all rules.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for rule in self.rules:
            if rule['pattern'].search(input_string):
                errors.append(rule['error_message'])
        
        return len(errors) == 0, errors


def create_default_input_validator() -> InputValidator:
    """Create input validator with default security rules."""
    validator = InputValidator()
    
    # Add common security rules
    validator.add_rule(
        "script_injection",
        r'<script.*?>|javascript:|vbscript:',
        "Potential script injection detected"
    )
    
    validator.add_rule(
        "sql_injection", 
        r"'\s*(OR|AND)\s*'|;\s*(DROP|DELETE|UPDATE)",
        "Potential SQL injection detected"
    )
    
    validator.add_rule(
        "path_traversal",
        r'.\./|\..[\/]',
        "Path traversal attempt detected"
    )
    
    return validator