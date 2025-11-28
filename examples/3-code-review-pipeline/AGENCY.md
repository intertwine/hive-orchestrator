---
project_id: code-review-pipeline-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, pipeline, review, iteration, quality, tutorial]
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
---

# Code Review Pipeline Example

## Objective
Demonstrate an iterative refinement workflow where code goes through multiple quality gates: Write → Review → Refine → Final Review.

**Scenario**: Build a secure user authentication module that goes through rigorous review before being considered production-ready.

## Pipeline Stages

```
Write → Review → Refine → Final Review → Approve
 (A)     (B)      (A)         (B)         (B)
```

## Tasks

### Stage 1: Initial Implementation (Agent A - Developer)
- [ ] Implement user authentication module
- [ ] Include password hashing (bcrypt)
- [ ] Add JWT token generation
- [ ] Implement basic input validation
- [ ] Write initial tests

### Stage 2: First Review (Agent B - Reviewer)
- [ ] Security audit (SQL injection, XSS, timing attacks)
- [ ] Code quality check (naming, structure, documentation)
- [ ] Test coverage analysis
- [ ] Performance review
- [ ] Document findings and required changes

### Stage 3: Refinement (Agent A - Developer)
- [ ] Address all security concerns
- [ ] Implement reviewer suggestions
- [ ] Add missing test cases
- [ ] Improve documentation
- [ ] Optimize performance issues

### Stage 4: Final Review (Agent B - Reviewer)
- [ ] Verify all issues addressed
- [ ] Re-audit security
- [ ] Confirm test coverage >90%
- [ ] Approve for production OR request additional changes

## Code Review Findings

### Review #1 (Initial)
<!-- Agent B: Document your findings here -->

**Security Issues:**
-

**Code Quality:**
-

**Testing:**
-

**Performance:**
-

**Required Changes:**
-

### Review #2 (Final)
<!-- Agent B: Final approval or additional concerns -->

**Status:**
- [ ] APPROVED for production
- [ ] REQUIRES additional changes

**Outstanding Issues:**
-

## Implementation Notes

### Version 1 (Initial)
<!-- Agent A: Describe your initial implementation -->

### Version 2 (Refined)
<!-- Agent A: Describe changes made based on review -->

## Agent Notes
<!-- Add timestamped notes as you work -->

## Workflow Protocol

### Agent A - Developer (Suggested: `anthropic/claude-3.5-sonnet`)

**Round 1:**
1. Set `owner` to your model name
2. Implement `src/auth.py` with authentication logic
3. Create `tests/test_auth.py` with test cases
4. Update "Implementation Notes - Version 1"
5. Mark Stage 1 tasks complete
6. Set `owner: null` and wait for review

**Round 2:**
1. Read review findings carefully
2. Set `owner` to your model name
3. Address ALL identified issues
4. Update code and tests
5. Update "Implementation Notes - Version 2"
6. Mark Stage 3 tasks complete
7. Set `owner: null` and wait for final review

### Agent B - Reviewer (Suggested: `anthropic/claude-3.5-sonnet` or `opus`)

**Round 1:**
1. Wait for Stage 1 completion (check tasks + owner field)
2. Set `owner` to your model name
3. Read `src/auth.py` and `tests/test_auth.py`
4. Perform comprehensive security + quality review
5. Document findings in "Review #1" section
6. Mark Stage 2 tasks complete
7. Set `owner: null` to trigger refinement

**Round 2:**
1. Wait for Stage 3 completion
2. Set `owner` to your model name
3. Verify all changes address your feedback
4. Perform final security audit
5. Update "Review #2" section
6. Mark approval checkbox or request more changes
7. Mark Stage 4 tasks complete
8. Set `status: completed` if approved
9. Set `owner: null`

## Quality Gates

Code must pass ALL these checks:

- [x] ✅ No SQL injection vulnerabilities
- [x] ✅ No XSS vulnerabilities
- [x] ✅ No timing attack vulnerabilities
- [x] ✅ Passwords properly hashed (bcrypt with salt)
- [x] ✅ JWTs properly signed and validated
- [x] ✅ Input validation on all user inputs
- [x] ✅ Test coverage >90%
- [x] ✅ All functions documented
- [x] ✅ Error handling implemented
- [x] ✅ No hardcoded secrets

## Iteration Limit

**Maximum 3 review cycles**

If not approved after 3 cycles:
- Set `blocked: true`
- Set `blocking_reason: "Requires human architectural review"`
- Escalate to human developer

## Coordination Approaches

Review pipelines involve multiple handoffs between the same agents. Choose your coordination method:

### Approach A: Git-Only (Default)
Use `owner` field in frontmatter to track who's currently working.

### Approach B: MCP Server (Programmatic)
AI agents use MCP tools for claiming and state updates.

**Developer Agent A**:
```
1. claim_project("code-review-pipeline-example", "claude-sonnet")
2. Implement authentication module
3. add_note(..., "Stage 1 complete - ready for review")
4. release_project(...)
```

**Reviewer Agent B**:
```
1. get_ready_work()  # Check if project is unclaimed
2. claim_project("code-review-pipeline-example", "claude-opus")
3. Review code, document findings
4. add_note(..., "Review complete - 3 issues found")
5. release_project(...)
```

### Approach C: HTTP Coordination (Real-time)
Use coordination server for immediate handoff notifications.

```bash
# Agent A finishes implementation
curl -X DELETE http://localhost:8080/release/code-review-pipeline-example

# Agent B immediately picks up
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "code-review-pipeline-example", "agent_name": "claude-opus", "ttl_seconds": 3600}'
```

**Benefits for review pipelines**:
- Instant handoff between iterations
- No git polling needed
- Clear audit trail of claims

### Approach D: Combined MCP + Coordination (Production)
Best for iterative workflows with tight feedback loops.

**Each iteration**:
1. `coordinator_claim(...)` - acquire lock
2. `claim_project(...)` - update AGENCY.md
3. Do work (implement/review)
4. `add_note(...)` - document progress
5. `release_project(...)` - update state
6. `coordinator_release(...)` - signal completion
