# Code Review Pipeline Example

## Overview

This example demonstrates **iterative refinement** through a structured review process. Code goes through multiple quality gates with feedback loops, similar to real-world development workflows.

## Pattern: Write → Review → Refine → Approve

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  Agent A │─────▶│  Agent B │─────▶│  Agent A │─────▶│  Agent B │
│  (Write) │      │ (Review) │      │ (Refine) │      │ (Approve)│
│  Sonnet  │      │  Opus    │      │  Sonnet  │      │  Opus    │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
     v1              Issues            v2             ✓ Approved
```

## Use Case

Perfect for:
- **Quality assurance**: Ensure production-ready code
- **Security-critical code**: Authentication, payments, data handling
- **Learning**: Developer agent learns from reviewer feedback
- **Compliance**: Meet coding standards and best practices

## How to Run

### Full Pipeline Execution

**Round 1: Initial Implementation**

```bash
# Step 1: Generate context for Agent A
make session PROJECT=examples/3-code-review-pipeline

# Step 2: In AI interface (Claude Sonnet):
# - Implement src/auth.py with authentication logic
# - Create tests/test_auth.py
# - Mark Stage 1 complete
# - Set owner: null
```

**Round 2: First Review**

```bash
# Step 3: Generate context for Agent B
make session PROJECT=examples/3-code-review-pipeline

# Step 4: In AI interface (Claude Opus or Sonnet):
# - Read the implementation
# - Perform security audit
# - Document findings in AGENCY.md
# - Mark Stage 2 complete
# - Set owner: null
```

**Round 3: Refinement**

```bash
# Step 5: Agent A returns to address feedback
make session PROJECT=examples/3-code-review-pipeline

# Step 6: In AI interface:
# - Read review findings
# - Fix all identified issues
# - Update code and tests
# - Mark Stage 3 complete
# - Set owner: null
```

**Round 4: Final Review**

```bash
# Step 7: Agent B performs final check
make session PROJECT=examples/3-code-review-pipeline

# Step 8: In AI interface:
# - Verify fixes
# - Approve or request more changes
# - Mark Stage 4 complete
# - Set status: completed if approved
```

## Expected Output

After completion:

1. **Production-ready authentication module** (`src/auth.py`):
   - Secure password hashing
   - JWT token generation/validation
   - Input sanitization
   - Comprehensive error handling

2. **High-quality test suite** (`tests/test_auth.py`):
   - >90% code coverage
   - Security test cases
   - Edge case handling

3. **Documented review process** in AGENCY.md:
   - Initial review findings
   - Refinement notes
   - Final approval

4. **Git history** showing iterative improvement:
   - Commit 1: Initial implementation
   - Commit 2: Address review findings
   - Commit 3: Final approval

## Key Concepts Demonstrated

### 1. Feedback Loops

Agent A's work is improved by Agent B's feedback:

```markdown
# Review #1
**Security Issues:**
- Password hashing uses MD5 (weak, use bcrypt)
- JWT secret is hardcoded

# Version 2
**Changes:**
- Switched to bcrypt with salt rounds
- JWT secret from environment variable
```

### 2. Quality Gates

Code must pass all checks before approval:

```python
# Initial (fails review)
def hash_password(password):
    return md5(password).hexdigest()  # ❌ Weak

# Refined (passes review)
import bcrypt
def hash_password(password):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt)  # ✅ Secure
```

### 3. Role Specialization

- **Agent A (Developer)**: Focuses on implementation
- **Agent B (Reviewer)**: Focuses on quality, security, standards

Different perspectives catch more issues!

### 4. Iteration Limits

Prevent infinite loops:
```yaml
blocked: true
blocking_reason: "Failed review 3 times, needs human architect"
```

## Benefits of Review Pipeline

### Higher Quality
- **Security**: Catches vulnerabilities before production
- **Maintainability**: Enforces coding standards
- **Reliability**: Higher test coverage
- **Documentation**: Reviewer ensures docs exist

### Learning
- Developer agent improves over iterations
- Patterns emerge (what passes review vs fails)
- Builds institutional knowledge

### Risk Reduction
- Critical code gets extra scrutiny
- Multiple "eyes" on the code
- Automated quality checks

## Review Checklist

Agent B should verify:

**Security:**
- [ ] No SQL injection vulnerabilities
- [ ] No XSS/CSRF vulnerabilities
- [ ] No hardcoded secrets
- [ ] Proper input validation
- [ ] Secure cryptography (bcrypt, not MD5)
- [ ] No timing attacks possible

**Code Quality:**
- [ ] Clear, descriptive names
- [ ] DRY (Don't Repeat Yourself)
- [ ] Appropriate error handling
- [ ] Follows project conventions
- [ ] No code smells

**Testing:**
- [ ] Coverage >90%
- [ ] Tests are clear and focused
- [ ] Edge cases covered
- [ ] Security scenarios tested

**Documentation:**
- [ ] Functions documented
- [ ] Complex logic explained
- [ ] Usage examples provided

**Performance:**
- [ ] No obvious inefficiencies
- [ ] Appropriate data structures
- [ ] Database queries optimized

## Variations to Try

### Different Review Depths

**Light Review (Fast)**
```markdown
Tasks:
- [ ] Run linter
- [ ] Check test coverage
- [ ] Quick security scan
```

**Standard Review (This Example)**
```markdown
Tasks:
- [ ] Security audit
- [ ] Code quality
- [ ] Test coverage
- [ ] Performance check
```

**Deep Review (Thorough)**
```markdown
Tasks:
- [ ] Full security penetration testing
- [ ] Architectural review
- [ ] Scalability analysis
- [ ] Accessibility audit
- [ ] Performance profiling
```

### Different Agent Combinations

**Same Model (Sonnet-Sonnet)**
- Pro: Consistent style
- Con: Same blind spots

**Different Models (Sonnet-Opus)**
- Pro: Different perspectives
- Con: Higher cost

**Cross-Vendor (Claude-GPT4)**
- Pro: Maximum diversity
- Con: Different coding styles

### Multi-Reviewer

Add more reviewers:
```
Write → Security Review → Code Review → Performance Review → Approve
 (A)         (B)              (C)            (D)            (E)
```

### Automated Checks

Add static analysis:
```
Write → Lint → Security Scan → Human Review → Approve
 (A)    (Auto)    (Auto)          (B)         (B)
```

## Real-World Applications

### Backend API Development
- Write: Implement endpoint
- Review: API design, security, validation
- Refine: Address feedback
- Approve: Merge to main

### Database Schema Changes
- Write: Design migration
- Review: Check for breaking changes, performance
- Refine: Optimize indexes, add constraints
- Approve: Deploy to staging

### Documentation
- Write: Create docs
- Review: Technical accuracy, clarity
- Refine: Improve examples, fix errors
- Approve: Publish

### UI Components
- Write: Build component
- Review: Accessibility, UX, responsiveness
- Refine: Fix a11y issues, improve UX
- Approve: Add to design system

## Troubleshooting

**Agent A doesn't wait for review:**
- Check workflow protocol
- Ensure Stage 1 completion before Stage 3
- Use `owner` field to coordinate

**Agent B too lenient/strict:**
- Adjust quality gates in AGENCY.md
- Provide examples of acceptable code
- Set clear standards

**Infinite refinement loop:**
- Enforce 3-iteration limit
- Set `blocked: true` after limit
- Escalate to human

**Changes not addressing feedback:**
- Make review feedback more specific
- Include code examples in review
- Agent A must read "Code Review Findings" section

## Metrics to Track

Monitor review effectiveness:

```markdown
## Review Metrics
- Issues found in Review #1: 8
- Issues fixed in v2: 8
- Issues found in Review #2: 0
- Review cycles: 2
- Time to approval: 45 minutes
- Test coverage: 95%
```

## Next Steps

- Try **Example 4: Multi-Model Ensemble** for competitive approaches
- Try **Example 5: Data Pipeline** for ETL workflows
- Try **Example 7: Complex Application** for multi-stage projects

---

**Estimated time**: 60-90 minutes
**Difficulty**: Advanced
**Models required**: 2 (recommend Sonnet + Opus)
**Quality improvement**: 3-5x fewer production bugs
