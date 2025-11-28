---
project_id: data-pipeline-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, pipeline, etl, data, sequential, tutorial]
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
---

# Data Pipeline (ETL) Workflow Example

## Objective
Demonstrate a classic Extract-Transform-Load (ETL) pipeline where data flows through multiple sequential processing stages, each handled by a specialized agent.

**Scenario**: Process raw customer transaction data from multiple sources, clean and enrich it, then load into a data warehouse for analytics.

## Pipeline Architecture

```
Extract → Validate → Transform → Enrich → Load → Verify
 (A)       (B)        (C)        (D)      (E)     (F)
```

## Data Flow

**Input**: Raw transaction files (CSV, JSON, XML)
**Output**: Clean, enriched data in analytics warehouse

## Tasks

### Stage 1: Extract (Agent A - Extractor)
- [ ] Read data from 3 sources (CSV, JSON, XML)
- [ ] Parse different formats into common structure
- [ ] Handle encoding issues and malformed data
- [ ] Output: `data/raw_extracted.json`
- [ ] Document row counts and issues found

### Stage 2: Validate (Agent B - Validator)
- [ ] Check data types (dates, amounts, IDs)
- [ ] Validate required fields present
- [ ] Flag invalid records
- [ ] Generate validation report
- [ ] Output: `data/validated.json` + `reports/validation_report.md`

### Stage 3: Transform (Agent C - Transformer)
- [ ] Standardize date formats (ISO 8601)
- [ ] Normalize currency (all to USD)
- [ ] Calculate derived fields (tax, total_with_tax)
- [ ] Deduplicate records
- [ ] Output: `data/transformed.json`

### Stage 4: Enrich (Agent D - Enricher)
- [ ] Add customer demographic data (mock lookup)
- [ ] Add product category information
- [ ] Calculate customer lifetime value
- [ ] Add geographic region
- [ ] Output: `data/enriched.json`

### Stage 5: Load (Agent E - Loader)
- [ ] Generate SQL INSERT statements
- [ ] Create warehouse schema
- [ ] Implement batch loading logic
- [ ] Handle conflicts (upsert strategy)
- [ ] Output: `data/warehouse_load.sql` + `schema.sql`

### Stage 6: Verify (Agent F - Verifier)
- [ ] Validate row counts match (with acceptable loss)
- [ ] Verify data quality metrics
- [ ] Check for duplicates in final output
- [ ] Generate pipeline summary report
- [ ] Output: `reports/pipeline_summary.md`

## Sample Input Data

```json
// data/source_a.csv (100 records)
date,customer_id,product_id,amount,currency
2024-11-01,C001,P123,99.99,USD
...

// data/source_b.json (150 records)
[
  {"timestamp": "2024-11-01T14:30:00", "customer": "C002", "product": "P456", "price": 149.99},
  ...
]

// data/source_c.xml (50 records)
<transactions>
  <transaction date="2024-11-01" customer_id="C003" product_id="P789" amount="199.99" />
  ...
</transactions>
```

## Pipeline Metrics

### Data Volume
- **Input**: 300 records (CSV: 100, JSON: 150, XML: 50)
- **After Validation**: ? records (? rejected)
- **After Transform**: ? records (? duplicates removed)
- **After Enrich**: ? records
- **Final Load**: ? records

### Quality Metrics
- **Completeness**: ?% (records with all required fields)
- **Accuracy**: ?% (valid data types)
- **Consistency**: ?% (normalized formats)
- **Uniqueness**: ?% (deduplicated)

## Stage Outputs

### Stage 1: Extract
<!-- Agent A: Document extraction results -->
- Rows extracted: ?
- Parsing errors: ?
- Encoding issues: ?

### Stage 2: Validate
<!-- Agent B: Document validation results -->
- Valid records: ?
- Invalid records: ?
- Common issues: ?

### Stage 3: Transform
<!-- Agent C: Document transformation results -->
- Rows transformed: ?
- Duplicates removed: ?
- Format conversions: ?

### Stage 4: Enrich
<!-- Agent D: Document enrichment results -->
- Rows enriched: ?
- Lookup failures: ?
- New fields added: ?

### Stage 5: Load
<!-- Agent E: Document load results -->
- Rows loaded: ?
- SQL statements generated: ?
- Load strategy: ?

### Stage 6: Verify
<!-- Agent F: Document verification results -->
- Pipeline success: ?
- Data quality score: ?
- Issues found: ?

## Agent Notes
<!-- Add timestamped notes as you work -->

## Workflow Protocol

### All Agents: Follow Sequential Order!

**Critical**: Each stage depends on the previous stage's output. Do NOT start until previous agent completes.

---

### Agent A - Extractor (Suggested: `anthropic/claude-haiku-4.5`)

1. Set `owner` to your model name
2. Create `data/` directory
3. Generate sample input files (CSV, JSON, XML) with 300 total records
4. Implement `scripts/extract.py` to parse all formats
5. Run extraction, output to `data/raw_extracted.json`
6. Document extraction results in "Stage 1" section
7. Mark Stage 1 tasks complete
8. Set `owner: null`

---

### Agent B - Validator (Suggested: `anthropic/claude-haiku-4.5`)

**Wait for Agent A to complete!**

1. Set `owner` to your model name
2. Read `data/raw_extracted.json`
3. Implement `scripts/validate.py` with validation rules
4. Generate `reports/validation_report.md`
5. Output clean data to `data/validated.json`
6. Document validation results in "Stage 2" section
7. Mark Stage 2 tasks complete
8. Set `owner: null`

---

### Agent C - Transformer (Suggested: `anthropic/claude-3.5-sonnet`)

**Wait for Agent B to complete!**

1. Set `owner` to your model name
2. Read `data/validated.json`
3. Implement `scripts/transform.py` with transformation logic
4. Apply standardizations and deduplication
5. Output to `data/transformed.json`
6. Document transformation results in "Stage 3" section
7. Mark Stage 3 tasks complete
8. Set `owner: null`

---

### Agent D - Enricher (Suggested: `anthropic/claude-3.5-sonnet`)

**Wait for Agent C to complete!**

1. Set `owner` to your model name
2. Read `data/transformed.json`
3. Implement `scripts/enrich.py` with enrichment logic
4. Add customer, product, geographic data
5. Output to `data/enriched.json`
6. Document enrichment results in "Stage 4" section
7. Mark Stage 4 tasks complete
8. Set `owner: null`

---

### Agent E - Loader (Suggested: `anthropic/claude-haiku-4.5`)

**Wait for Agent D to complete!**

1. Set `owner` to your model name
2. Read `data/enriched.json`
3. Implement `scripts/load.py` with SQL generation
4. Create `schema.sql` with warehouse schema
5. Generate `data/warehouse_load.sql` with INSERT statements
6. Document load results in "Stage 5" section
7. Mark Stage 5 tasks complete
8. Set `owner: null`

---

### Agent F - Verifier (Suggested: `anthropic/claude-haiku-4.5`)

**Wait for Agent E to complete!**

1. Set `owner` to your model name
2. Implement `scripts/verify.py` to check data quality
3. Compare input vs output row counts
4. Calculate quality metrics
5. Generate `reports/pipeline_summary.md`
6. Update "Pipeline Metrics" section
7. Mark Stage 6 tasks complete
8. Set `status: completed` and `owner: null`

## Data Quality Standards

Pipeline passes if:
- ✅ Data loss <5% (acceptable for invalid records)
- ✅ No duplicates in final output
- ✅ 100% of loaded records have required fields
- ✅ All dates in ISO 8601 format
- ✅ All currencies normalized to USD

## Error Handling

If any stage fails:
1. Document issue in stage output section
2. Set `blocked: true`
3. Set `blocking_reason: "Stage X failed: [description]"`
4. Previous stage agent may need to fix output

## Pipeline Monitoring

Track these metrics:
- **Throughput**: Records processed per stage
- **Quality**: Validation pass rate
- **Latency**: Time per stage (simulated)
- **Data loss**: Input vs output record count

## Coordination Approaches

Data pipelines with strict ordering benefit from dependency tracking and coordination.

### Using Structured Dependencies

For complex pipelines, consider splitting into separate projects with dependencies:

```yaml
# stage-2-validate/AGENCY.md
dependencies:
  blocked_by: [data-pipeline-stage-1]  # Wait for extraction
  blocks: [data-pipeline-stage-3]      # Transformation waits on us
```

This allows `get_ready_work()` to automatically determine which stage is next.

### Approach A: Git-Only (Simple)
Sequential handoff using `owner` field. Each agent waits for previous to complete.

### Approach B: MCP Server (Programmatic)
AI agents use MCP tools to track pipeline progress.

**Stage N Agent**:
```
1. get_ready_work()  # Only returns if stage N-1 complete
2. claim_project("data-pipeline-example", "agent-name")
3. Process data
4. add_note(..., "Stage N complete: X records processed")
5. release_project(...)
```

**Check dependencies**:
```
get_dependencies("data-pipeline-example")
# Returns: {"blocked_by": [...], "all_dependencies_met": true}
```

### Approach C: HTTP Coordination (Ordered Execution)
Use coordination server to enforce strict stage ordering.

```bash
# Stage 1 agent completes
curl -X DELETE http://localhost:8080/release/pipeline-stage-1

# Stage 2 agent checks if previous stage released
curl http://localhost:8080/status/pipeline-stage-1
# If released, proceed to claim stage 2

curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "pipeline-stage-2", "agent_name": "validator", "ttl_seconds": 1800}'
```

### Approach D: Combined MCP + Coordination (Production ETL)
For production data pipelines:

1. Use separate claim IDs per stage: `pipeline-stage-1`, `pipeline-stage-2`, etc.
2. Check previous stage completion before claiming next
3. Use `coordinator_reservations()` to see pipeline status

**Pipeline orchestration pattern**:
```
# Check all stage statuses
coordinator_reservations()
# Find next unclaimed, unblocked stage
get_ready_work()
# Claim and process
coordinator_claim("pipeline-stage-N", "agent", 3600)
```
