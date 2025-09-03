# Storage Directory

## Overview

The storage directory serves as the centralized data repository for the AI Data Engineer Bootcamp, providing sample datasets and documents that support various module implementations. This directory contains real-world data files used throughout the bootcamp exercises, from invoice processing to restaurant analytics.

## Directory Structure

```
storage/
├── csv/        # Structured tabular data
├── doc/        # Word documents with unstructured content
├── json/       # Semi-structured data files
└── pdf/        # Document collections for processing
    ├── invoice/  # Uber Eats invoice samples
    └── menu/     # Restaurant menu documents
```

## Purpose and Function

This directory fulfills several critical roles in the bootcamp infrastructure:

### Data Source Management
Provides consistent, versioned datasets that modules can reliably access for processing pipelines. Each file type represents different data engineering challenges and processing requirements.

### Module Support
Different modules leverage specific data formats to demonstrate various processing techniques:
- **Module 1**: Processes PDF invoices for structured data extraction
- **Module 2**: Uses restaurant data for RAG implementations
- **Module 3**: Transforms natural language queries against structured datasets
- **Module 4**: Orchestrates multi-source data processing
- **Module 5**: Analyzes transactional data for fraud detection patterns

### Testing and Validation
Serves as ground truth for validating extraction accuracy, transformation correctness, and pipeline reliability across all modules.

## Data Categories

### PDF Documents (`/pdf`)

#### Invoice Collection (`/pdf/invoice`)
Contains 20 Uber Eats invoice PDFs organized by module requirements:
- **inv-mod-1-XX.pdf**: Basic invoice formats for initial extraction exercises
- **inv-mod-2-XX.pdf**: Complex invoices with multiple items and discounts
- **inv-mod-3-XX.pdf**: Advanced formats requiring sophisticated parsing

These invoices feature varying complexity levels including:
- Single and multi-item orders
- Different discount types and promotions
- Delivery fees and service charges
- Multiple payment methods
- International and domestic formats

#### Menu Collection (`/pdf/menu`)
Restaurant menus from 8 different cuisines:
- American, Chinese, French, Indian
- Italian, Japanese, Mexican, Thai

Each menu PDF contains structured information about:
- Dish names and descriptions
- Pricing information
- Dietary restrictions and allergen warnings
- Category organization (appetizers, mains, desserts)

### Structured Data (`/csv`)

#### Coupons Dataset
**File**: `coupons_2025-07-31.csv`

Comprehensive promotional data containing:
- Coupon codes and descriptions
- Discount types (percentage, fixed value, combo offers)
- Minimum order requirements
- User categories (new users, anniversary, loyalty)
- Usage statistics and validity periods
- Status tracking (active, expired, suspended)

Sample structure:
```csv
Código,Descrição,Tipo,Valor,Pedido Mínimo,Categoria,Validade,Uso Máximo,Usos Atuais,Status
```

### Semi-Structured Data (`/json`)

#### Restaurant Database
**File**: `restaurants.json`

Detailed restaurant information including:
- Restaurant profiles with ratings and price ranges
- Cuisine types and specialties
- Delivery zones and operational hours
- Menu items with allergen information
- Promotional offers and discounts
- Geographic coordinates for mapping
- Emergency contact information

The JSON structure supports:
- Nested objects for complex relationships
- Arrays for multiple values (menu items, delivery zones)
- Metadata for version control and updates
- Reference links to related documents

### Document Resources (`/doc`)

#### Allergy Guidelines
**File**: `allergy.docx`

Comprehensive documentation covering:
- Common food allergens and their classifications
- Restaurant compliance requirements
- Customer communication protocols
- Emergency response procedures
- Legal requirements and regulations

## Usage Patterns

### Direct File Access
Modules access files using absolute or relative paths:

```python
invoice_path = "storage/pdf/invoice/inv-mod-1-01.pdf"
```

### Batch Processing
Pipeline configurations often process entire directories:

```python
invoice_directory = "storage/pdf/invoice/"
```

### Cross-Module Sharing
Shared datasets enable consistent testing across modules while demonstrating different processing approaches on the same source data.

## Data Characteristics

### Volume Metrics
- Total Files: 31
- PDF Documents: 28 (invoices + menus)
- Structured Data: 1 CSV file with 8,617 bytes
- Semi-Structured: 1 JSON file with 19,441 bytes
- Documentation: 1 DOCX file with 592,629 bytes

### Quality Attributes
- **Consistency**: Standardized naming conventions across all files
- **Completeness**: Full datasets without missing critical fields
- **Variety**: Multiple formats demonstrating real-world complexity
- **Veracity**: Realistic data patterns matching production scenarios

## Best Practices

### File Naming Conventions
- Use lowercase with hyphens for separators
- Include module identifiers where applicable
- Maintain version suffixes for dataset iterations
- Date stamps for time-sensitive data (YYYY-MM-DD format)

### Data Privacy
All data in this directory is synthetic or anonymized. Personal information has been removed or replaced with fictional alternatives while maintaining structural integrity for processing exercises.

### Access Patterns
- Read-only access for pipeline processing
- Cached results stored in separate output directories
- Original files preserved for repeatability
- Version control tracking for all changes

## Integration Points

### Apache Airflow DAGs
DAGs reference storage paths for file sensors and processing tasks, enabling event-driven pipeline triggers when new files arrive.

### MinIO Object Storage
Files can be uploaded to MinIO buckets for distributed processing, maintaining the same organizational structure in cloud storage.

### Database Loading
Processed data from storage files populates PostgreSQL tables for downstream analytics and reporting.

## Maintenance Guidelines

### Adding New Data
When contributing new datasets:
1. Follow existing naming conventions
2. Update this README with dataset descriptions
3. Ensure data quality and privacy compliance
4. Test with relevant module pipelines
5. Document any special processing requirements

### Archiving Old Data
Obsolete datasets should be moved to an archive directory rather than deleted, maintaining historical context for previous bootcamp versions.

## Module-Specific Usage

### Module 1: Document Extract
Processes all invoice PDFs to extract structured data including:
- Restaurant names and order details
- Item descriptions and quantities
- Pricing breakdowns and totals
- Delivery information and timestamps

### Module 2: RAG Agent
Utilizes restaurant JSON and menu PDFs to build knowledge bases for:
- Restaurant recommendation systems
- Menu search and discovery
- Dietary restriction filtering
- Price comparison analytics

### Module 3: Text-to-SQL
Transforms natural language queries against:
- Coupon database for promotional analytics
- Restaurant data for business intelligence
- Cross-referenced menu and pricing information

### Module 4: Multi-Agent
Orchestrates complex workflows combining:
- Invoice processing agents
- Restaurant data enrichment
- Coupon validation and application
- Customer preference analysis

### Module 5: Fraud Detection
Analyzes patterns across:
- Transaction histories from invoices
- Unusual coupon usage patterns
- Restaurant order anomalies
- Delivery pattern irregularities

## Future Enhancements

Planned additions to the storage directory:
- Streaming data samples for real-time processing
- Time-series datasets for predictive analytics
- Image files for computer vision exercises
- Audio transcripts for speech processing
- Geospatial data for location analytics

This storage directory forms the foundation for practical, hands-on learning throughout the AI Data Engineer Bootcamp, providing diverse, realistic datasets that challenge students to build robust, production-ready data pipelines.