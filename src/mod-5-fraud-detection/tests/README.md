# Tests Documentation

This folder contains organized tests for the fraud detection system with CrewAI agents and Qdrant integration.

## Folder Structure

```
tests/
├── core/           # Essential working tests
├── integration/    # System integration tests  
├── dev/           # Development utilities
└── README.md      # This documentation
```

## Core Tests (`tests/core/`)

Essential tests that verify the fraud detection system is working correctly:

### `test_qdrant_summary.py` ✅
- **Purpose**: Quick system health check
- **Tests**: Qdrant connection, fraud pattern detection, velocity fraud analysis
- **Usage**: `python tests/core/test_qdrant_summary.py`
- **Expected Output**: System summary with pattern count and fraud detection results

### `test_direct_agents_clean.py` ✅  
- **Purpose**: Complete CrewAI agent pipeline validation
- **Tests**: Multi-agent fraud analysis, pattern detection, risk scoring
- **Usage**: `python tests/core/test_direct_agents_clean.py`
- **Expected Output**: Detailed agent analysis for 5 test orders with JSON output

### `validate_fraud_detection.py` ✅
- **Purpose**: Comprehensive fraud detection accuracy validation
- **Tests**: 9 fraud scenarios, pattern matching, Qdrant utilization
- **Usage**: `python tests/core/validate_fraud_detection.py`
- **Expected Output**: Detailed validation report with accuracy metrics

## Integration Tests (`tests/integration/`)

Tests that verify component integration (may need Spark/Kafka fixes):

### `test_full_integration.py` ⚠️
- **Purpose**: End-to-end pipeline testing
- **Status**: Has Spark Java version issues
- **Tests**: Component setup, Qdrant connection, fraud processing, data enrichment

### `test_kafka_qdrant_integration.py` ⚠️
- **Purpose**: Kafka → Qdrant integration testing  
- **Status**: Kafka connection issues (expected without data generator)
- **Tests**: Kafka consumer, Qdrant pattern matching, streaming simulation

## Development Utilities (`tests/dev/`)

Helper tools for development and debugging:

### `test_agents_direct.py` 🔧
- **Purpose**: Simple CrewAI agent functionality test
- **Usage**: Quick agent verification during development

### `test_prompt_management.py` 🔧
- **Purpose**: Prompt template system testing
- **Usage**: Verify agent prompt loading and formatting

### `run_all_tests.py` 🔧
- **Purpose**: Test runner for multiple test execution
- **Usage**: Batch test execution utility

## Usage Examples

```bash
# Run core system validation
python tests/core/test_qdrant_summary.py

# Test full agent pipeline  
python tests/core/test_direct_agents_clean.py

# Comprehensive accuracy validation
python tests/core/validate_fraud_detection.py

# Development agent testing
python tests/dev/test_agents_direct.py
```

## Test Status

- ✅ **Working**: Core tests are fully functional
- ⚠️ **Needs Fix**: Integration tests have known Spark/Kafka issues
- 🔧 **Development**: Utility tests for development workflow

## Integration with CI/CD

Core tests can be integrated into CI/CD pipelines for automated validation:

```bash
# Essential validation pipeline
python tests/core/test_qdrant_summary.py
python tests/core/validate_fraud_detection.py
```

## Requirements

All tests require:
- Python 3.12+
- Qdrant cloud access (configured in environment)
- OpenAI API key (for CrewAI agents)
- Required dependencies from requirements.txt

Integration tests additionally require:
- Apache Spark (Java 17+)
- Kafka access (for streaming tests)