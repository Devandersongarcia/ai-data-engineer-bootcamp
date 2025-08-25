# LLM Integration Specialist

## Expertise Areas

- OpenAI API integration and optimization
- Prompt engineering for invoice processing
- Error handling and cost optimization
- Confidence scoring and validation

## Core Integration Patterns

### Structured LLM Extraction
```python
import json
from typing import Dict, Any
from openai import AsyncOpenAI

class LLMExtractor:
    """Handle structured data extraction using LLM."""
    
    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4"):
        self.client = client
        self.model = model

    async def extract_structured_data(
        self, 
        raw_text: str, 
        extraction_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured data using model-specific prompts."""
        prompt = extraction_config["prompt"].format(
            raw_text=raw_text,
            expected_fields=extraction_config["fields"]
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
```

### Model Detection Strategy
```python
from enum import Enum
from dataclasses import dataclass

class InvoiceModel(Enum):
    """Supported invoice model types."""
    VENDOR_A = "vendor_a_v2"
    VENDOR_B = "vendor_b_v1" 
    GENERIC = "generic_fallback"

@dataclass
class ModelDetectionResult:
    """Result of model detection process."""
    model_type: InvoiceModel
    confidence: float
    reasoning: str

class ModelDetector:
    """Detect invoice model type using LLM analysis."""
    
    async def detect_model(self, raw_text: str) -> ModelDetectionResult:
        """Analyze text content to determine invoice model."""
        detection_prompt = self._build_detection_prompt(raw_text)
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": detection_prompt}],
            temperature=0.0
        )
        
        return self._parse_detection_response(response.choices[0].message.content)
```

## Confidence-Based Processing

### Confidence Validation
```python
from airflow.decorators import task

@task.skip_if(lambda ctx: below_confidence_threshold(ctx))
def high_confidence_extraction():
    """Process extraction only when confidence exceeds threshold."""
    pass

def below_confidence_threshold(context) -> bool:
    """Check if extraction confidence is below acceptable threshold."""
    extraction_result = context["ti"].xcom_pull(task_ids="extract_data")
    confidence = extraction_result.get("confidence", 0.0)
    threshold = context["params"].get("confidence_threshold", 0.75)
    
    return confidence < threshold
```

### Quality Assurance
```python
@task.run_if(lambda ctx: requires_validation(ctx))
def quality_validation():
    """Validate extraction results when required."""
    pass

def requires_validation(context) -> bool:
    """Determine if additional validation is needed."""
    result = context["ti"].xcom_pull(task_ids="extract_data")
    
    return (
        result.get("confidence", 1.0) < 0.9 or
        result.get("field_count", 0) < context["params"].get("min_fields", 5)
    )
```

## Error Handling and Resilience

### Retry Strategy
```python
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

class ResilientLLMClient:
    """LLM client with built-in resilience patterns."""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_with_retry(self, prompt: str) -> str:
        """Make LLM API call with automatic retry logic."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=30
            )
            return response.choices[0].message.content
            
        except Exception as e:
            self._log_api_error(e, prompt[:100])
            raise
```

### Circuit Breaker Pattern
```python
from datetime import datetime, timedelta

class LLMCircuitBreaker:
    """Circuit breaker for LLM API calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    async def call_protected(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
```

## Cost Optimization

### Token Management
```python
class TokenOptimizer:
    """Optimize token usage for cost efficiency."""
    
    def optimize_prompt(self, prompt: str, max_tokens: int = 3000) -> str:
        """Optimize prompt length while preserving essential information."""
        if len(prompt.split()) <= max_tokens:
            return prompt
            
        return self._truncate_intelligently(prompt, max_tokens)
    
    def _truncate_intelligently(self, text: str, max_tokens: int) -> str:
        """Truncate text while preserving critical sections."""
        sections = text.split('\n\n')
        critical_sections = [s for s in sections if self._is_critical(s)]
        
        result = '\n\n'.join(critical_sections)
        if len(result.split()) <= max_tokens:
            return result
            
        return result[:max_tokens * 4]  # Approximate token to char ratio
```

### Model Selection Strategy
```python
from enum import Enum

class ModelTier(Enum):
    """Different model tiers for cost optimization."""
    BASIC = "gpt-3.5-turbo"
    ADVANCED = "gpt-4"
    PREMIUM = "gpt-4-turbo"

class ModelSelector:
    """Select appropriate model based on task complexity."""
    
    def select_model(self, task_complexity: str, content_length: int) -> str:
        """Choose optimal model for task requirements."""
        if task_complexity == "simple" and content_length < 1000:
            return ModelTier.BASIC.value
        elif task_complexity == "complex" or content_length > 5000:
            return ModelTier.PREMIUM.value
        else:
            return ModelTier.ADVANCED.value
```

## Prompt Engineering Patterns

### Few-Shot Learning
```python
class PromptBuilder:
    """Build prompts with few-shot examples."""
    
    def build_extraction_prompt(
        self, 
        raw_text: str, 
        examples: List[Dict], 
        schema: Dict
    ) -> str:
        """Build prompt with examples for better extraction accuracy."""
        base_prompt = self._get_base_instruction()
        examples_section = self._format_examples(examples)
        schema_section = self._format_schema(schema)
        input_section = f"Input text:\n{raw_text}"
        
        return "\n\n".join([
            base_prompt,
            examples_section, 
            schema_section,
            input_section,
            "Output:"
        ])
```

### Validation Prompts
```python
class ValidationPromptBuilder:
    """Build prompts for result validation."""
    
    def build_validation_prompt(
        self, 
        original_text: str, 
        extraction_result: Dict
    ) -> str:
        """Build prompt to validate extraction accuracy."""
        return f"""
        Original text: {original_text}
        
        Extracted data: {json.dumps(extraction_result, indent=2)}
        
        Validate this extraction:
        1. Are all extracted values present in the original text?
        2. Are the values correctly formatted?
        3. What is the confidence level (0-1)?
        
        Return JSON with validation results.
        """
```

## Monitoring and Observability

### Performance Tracking
```python
import time
from contextlib import asynccontextmanager

class LLMMetrics:
    """Track LLM performance and usage metrics."""
    
    @asynccontextmanager
    async def track_api_call(self, operation: str):
        """Context manager to track API call metrics."""
        start_time = time.time()
        tokens_used = 0
        
        try:
            yield
            duration = time.time() - start_time
            self._record_success(operation, duration, tokens_used)
            
        except Exception as e:
            duration = time.time() - start_time 
            self._record_failure(operation, duration, str(e))
            raise
```

### Cost Monitoring
```python
class CostTracker:
    """Monitor and alert on LLM usage costs."""
    
    def __init__(self, daily_budget: float = 100.0):
        self.daily_budget = daily_budget
        self.current_spend = 0.0
    
    def record_usage(self, tokens: int, model: str) -> None:
        """Record token usage and calculate costs."""
        cost = self._calculate_cost(tokens, model)
        self.current_spend += cost
        
        if self.current_spend > self.daily_budget * 0.8:
            self._send_budget_alert()
```