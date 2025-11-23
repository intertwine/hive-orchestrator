# Data Pipeline (ETL) Workflow Example

## Overview

This example demonstrates a classic **Extract-Transform-Load (ETL)** pipeline with multiple sequential processing stages. Each stage is handled by a specialized agent, showcasing how Agent Hive can orchestrate complex data workflows.

## Pattern: Sequential Data Processing

```
┌─────────┐   ┌──────────┐   ┌───────────┐   ┌─────────┐   ┌──────┐   ┌────────┐
│ Extract │──▶│ Validate │──▶│ Transform │──▶│ Enrich  │──▶│ Load │──▶│ Verify │
│  (A)    │   │   (B)    │   │    (C)    │   │   (D)   │   │ (E)  │   │  (F)   │
└─────────┘   └──────────┘   └───────────┘   └─────────┘   └──────┘   └────────┘
   CSV            Check          Clean          Add           SQL         Report
   JSON           Types         Normalize      Context       INSERT     Metrics
   XML            Required      Dedupe         Lookups      Warehouse   Quality
```

## Use Case

Perfect for:
- **Data engineering**: Building production ETL pipelines
- **Data migration**: Moving data between systems
- **Data quality**: Multi-stage validation and cleansing
- **Analytics preparation**: Preparing data for BI tools

## How to Run

### Full Pipeline Execution

**Stage 1: Extract Data**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Haiku):
# - Generate sample data files (CSV, JSON, XML)
# - Implement extraction script
# - Parse all formats to common JSON
# - Mark Stage 1 complete
```

**Stage 2: Validate Data**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Haiku):
# - Read extracted data
# - Validate data types and required fields
# - Generate validation report
# - Mark Stage 2 complete
```

**Stage 3: Transform Data**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Sonnet):
# - Standardize formats
# - Deduplicate records
# - Calculate derived fields
# - Mark Stage 3 complete
```

**Stage 4: Enrich Data**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Sonnet):
# - Add customer demographics
# - Add product categories
# - Calculate lifetime value
# - Mark Stage 4 complete
```

**Stage 5: Load to Warehouse**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Haiku):
# - Generate warehouse schema
# - Create SQL INSERT statements
# - Implement load logic
# - Mark Stage 5 complete
```

**Stage 6: Verify Pipeline**

```bash
make session PROJECT=examples/5-data-pipeline

# In AI interface (Haiku):
# - Verify row counts
# - Calculate quality metrics
# - Generate summary report
# - Set status: completed
```

## Expected Output

After completion, your pipeline will have:

### 1. Data Files
```
examples/5-data-pipeline/
├── data/
│   ├── source_a.csv          # Input: 100 records
│   ├── source_b.json         # Input: 150 records
│   ├── source_c.xml          # Input: 50 records
│   ├── raw_extracted.json    # After Stage 1: 300 records
│   ├── validated.json        # After Stage 2: ~290 records
│   ├── transformed.json      # After Stage 3: ~280 records
│   ├── enriched.json         # After Stage 4: ~280 records
│   └── warehouse_load.sql    # After Stage 5: SQL INSERT
```

### 2. Processing Scripts
```
scripts/
├── extract.py       # Parses CSV, JSON, XML
├── validate.py      # Data validation rules
├── transform.py     # Normalization logic
├── enrich.py        # Data enrichment
├── load.py          # SQL generation
└── verify.py        # Quality checks
```

### 3. Reports
```
reports/
├── validation_report.md    # Validation issues found
└── pipeline_summary.md     # Final metrics and quality
```

### 4. Database Schema
```sql
-- schema.sql
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  transaction_date DATE NOT NULL,
  customer_id VARCHAR(50) NOT NULL,
  product_id VARCHAR(50) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  tax DECIMAL(10,2),
  total_with_tax DECIMAL(10,2),
  customer_segment VARCHAR(50),
  product_category VARCHAR(50),
  region VARCHAR(50),
  customer_ltv DECIMAL(10,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Key Concepts Demonstrated

### 1. Sequential Dependencies

Each stage requires previous stage's output:

```python
# Stage 2 depends on Stage 1
with open('data/raw_extracted.json') as f:
    data = json.load(f)  # ← Must exist from Stage 1

# Stage 3 depends on Stage 2
with open('data/validated.json') as f:
    data = json.load(f)  # ← Must exist from Stage 2
```

### 2. Data Quality Gates

Each stage improves data quality:

```markdown
Stage 1 (Extract): 300 records, raw formats
  ↓ Parse errors: 5 records lost
Stage 2 (Validate): 295 records, validated types
  ↓ Invalid data: 10 records flagged
Stage 3 (Transform): 285 records, normalized
  ↓ Duplicates: 5 records removed
Stage 4 (Enrich): 280 records, enriched
  ↓ Enrichment complete
Stage 5 (Load): 280 records ready for warehouse
  ↓ Load verified
Stage 6 (Verify): 280/300 = 93.3% quality rate ✓
```

### 3. Agent Specialization

Different agents for different complexity:

- **Haiku**: Extract, Validate, Load, Verify (simple parsing/validation)
- **Sonnet**: Transform, Enrich (complex logic, calculations)

Cost optimization: Use powerful models only where needed!

### 4. Error Propagation

Issue in Stage 2 blocks Stage 3:

```yaml
# Agent B finds critical issue
blocked: true
blocking_reason: "Stage 2 validation failed: 50% invalid dates"

# Agent C waits
owner: null  # Can't proceed until unblocked
```

## Data Transformation Examples

### Extract: Multi-format Parsing

```python
# CSV → JSON
{"date": "2024-11-01", "customer_id": "C001", "amount": 99.99}

# JSON → Common format
{"timestamp": "2024-11-01T14:30:00", "customer": "C002", "price": 149.99}
# → {"date": "2024-11-01", "customer_id": "C002", "amount": 149.99}

# XML → Common format
<transaction date="2024-11-01" customer_id="C003" amount="199.99" />
# → {"date": "2024-11-01", "customer_id": "C003", "amount": 199.99}
```

### Transform: Normalization

```python
# Before
{
  "date": "11/01/2024",           # US format
  "amount": 100,
  "currency": "EUR"
}

# After
{
  "date": "2024-11-01",           # ISO 8601
  "amount": 105.50,               # Converted to USD
  "currency": "USD",
  "tax": 8.44,                    # Calculated
  "total_with_tax": 113.94
}
```

### Enrich: Adding Context

```python
# Before
{
  "customer_id": "C001",
  "product_id": "P123"
}

# After
{
  "customer_id": "C001",
  "customer_segment": "Premium",
  "customer_ltv": 5420.50,
  "customer_region": "Northeast",
  "product_id": "P123",
  "product_category": "Electronics",
  "product_brand": "TechCorp"
}
```

## Benefits of Pipeline Pattern

### Separation of Concerns

Each stage has single responsibility:
- Extract: Only parsing
- Validate: Only validation
- Transform: Only normalization
- Enrich: Only enhancement
- Load: Only SQL generation
- Verify: Only quality checks

Easy to maintain and debug!

### Incremental Processing

See data evolve through stages:
```bash
# Check data after each stage
cat data/raw_extracted.json    # Stage 1 output
cat data/validated.json        # Stage 2 output
cat data/transformed.json      # Stage 3 output
```

### Reusability

Stages can be reused:
- Extract script works for any CSV/JSON/XML
- Validate logic applies to multiple pipelines
- Transform functions are generic

### Fault Tolerance

If Stage 3 fails:
- Stages 1-2 outputs are preserved
- Restart from Stage 3
- No need to reprocess earlier stages

## Variations to Try

### Parallel Stages

Some stages can run in parallel:

```
        ┌──────────────┐
   ┌───▶│ Transform A  │───┐
   │    └──────────────┘   │
Extract                      Merge → Load
   │    ┌──────────────┐   │
   └───▶│ Transform B  │───┘
        └──────────────┘
```

### Branching Pipelines

One input, multiple outputs:

```
Extract → Validate ─┬─▶ Analytics Pipeline → Data Warehouse
                    │
                    └─▶ Reporting Pipeline → CSV Reports
```

### Stream Processing

Continuous pipeline:

```
Stage 1 (Extract): Process batch every hour
Stage 2 (Validate): Stream validation
Stage 3 (Transform): Micro-batches
...
```

### Data Quality Feedback

Stage 6 reports issues back to Stage 1:

```
Verify: "50% of XML records have encoding issues"
  ↓ Feedback to Extract agent
Extract: Update parser to handle encoding better
```

## Real-World Applications

### E-commerce Analytics
1. **Extract**: Orders from Shopify API, payments from Stripe
2. **Validate**: Check order IDs, amounts, timestamps
3. **Transform**: Standardize currencies, timezones
4. **Enrich**: Add customer segments, product margins
5. **Load**: Insert into analytics warehouse
6. **Verify**: Ensure revenue matches source

### Log Processing
1. **Extract**: Parse server logs (Apache, Nginx, app logs)
2. **Validate**: Filter invalid log lines
3. **Transform**: Extract structured fields (IP, status, duration)
4. **Enrich**: Add geolocation, user agent parsing
5. **Load**: Insert into Elasticsearch
6. **Verify**: Check index health

### Customer Data Platform
1. **Extract**: Data from CRM, email, support tickets
2. **Validate**: Deduplicate customer records
3. **Transform**: Standardize addresses, phone numbers
4. **Enrich**: Calculate customer scores, segments
5. **Load**: Update customer master table
6. **Verify**: Ensure no duplicates, all fields populated

## Troubleshooting

**Stage N starts before Stage N-1 completes:**
- Check `owner` field is `null` before starting
- Verify previous stage tasks are marked complete
- Check that required output file exists

**Data validation fails at Stage 2:**
- Review `reports/validation_report.md`
- Agent A may need to improve parsing
- Adjust validation rules if too strict

**Row count decreases too much:**
- Check quality standards (5% loss acceptable)
- If >5% loss, investigate validation rules
- May need to improve data quality at source

**Pipeline takes too long:**
- Consider parallel stages where possible
- Use faster models (Haiku) for simple stages
- Batch processing instead of record-by-record

**Enrichment lookups fail:**
- For this example, use mock data
- In production, handle missing lookups gracefully
- Document lookup failure rate

## Performance Metrics

Track pipeline efficiency:

```markdown
## Pipeline Performance
- Total records in: 300
- Total records out: 280
- Data loss: 6.7% ✓ (under 5% threshold)
- Processing time: ~45 minutes (6 agents × ~7 min avg)
- Throughput: ~6 records/minute
- Quality score: 98.5% ✓

## Stage Breakdown
- Extract: 7 min (300 → 300 records)
- Validate: 6 min (300 → 295 records, 5 errors)
- Transform: 8 min (295 → 280 records, 15 dupes)
- Enrich: 9 min (280 → 280 records)
- Load: 5 min (280 SQL statements)
- Verify: 3 min (quality report)
```

## Next Steps

- Try **Example 6: Creative Collaboration** for non-data workflows
- Try **Example 7: Complex Application** for full development pipeline
- Extend this pipeline with additional stages (e.g., monitoring, alerting)

---

**Estimated time**: 60-90 minutes
**Difficulty**: Intermediate-Advanced
**Models required**: 6 (can reuse same models)
**Data quality improvement**: 10-20x vs manual processing
**Cost**: Moderate (mix of Haiku and Sonnet)
