# Complex Application Example: Full-Stack Development

## Overview

This example demonstrates a **comprehensive full-stack development workflow** that combines all Agent Hive patterns into a single cohesive project. It shows how to build a production-ready application using sequential phases, parallel execution, review cycles, and specialized agents.

## Pattern: Multi-Phase Development Lifecycle

```
PHASE 1: FOUNDATION (Sequential)
┌─────────┐   ┌──────────┐   ┌─────────┐
│ Design  │──▶│  Schema  │──▶│  Setup  │
│   (A)   │   │   (B)    │   │   (C)   │
└─────────┘   └──────────┘   └─────────┘

PHASE 2: CORE FEATURES (Parallel)
    ┌────────┐
    │ Auth   │
    │  (D)   │
    └────────┘
         ║
    ┌────────┐     All complete
    │ CRUD   │────────────────▶  Phase 3
    │  (E)   │
    └────────┘
         ║
    ┌────────┐
    │ Models │
    │  (F)   │
    └────────┘

PHASE 3: QUALITY (Review Pipeline)
┌───────┐   ┌────────┐   ┌───────┐   ┌────────┐
│ Test  │──▶│ Review │──▶│  Fix  │──▶│Approve │
│  (G)  │   │  (H)   │   │  (I)  │   │  (H)   │
└───────┘   └────────┘   └───────┘   └────────┘

PHASE 4: DOCUMENTATION (Sequential)
┌─────────┐   ┌──────────┐   ┌─────────┐
│ API Doc │──▶│  Deploy  │──▶│ README  │
│   (J)   │   │   (K)    │   │   (L)   │
└─────────┘   └──────────┘   └─────────┘

Final: Working Task Management API! 🚀
```

## What You'll Build

A production-ready **Task Management API** with:

### Features
- ✅ User registration and authentication (JWT)
- ✅ CRUD operations for tasks
- ✅ User-specific task isolation
- ✅ Secure password hashing (bcrypt)
- ✅ Input validation and error handling

### Quality
- ✅ >90% test coverage
- ✅ Security-reviewed code
- ✅ No SQL injection vulnerabilities
- ✅ Proper error responses

### Documentation
- ✅ Complete API documentation
- ✅ Deployment guide
- ✅ Developer README
- ✅ Auto-generated Swagger docs

## Use Case

Perfect for:
- **Learning full-stack development**: Complete end-to-end example
- **Production applications**: Real patterns that scale
- **Team coordination**: How multiple developers collaborate
- **Best practices**: Security, testing, documentation

## How to Run

### Phase 1: Foundation (Sequential - ~45 min)

**Step 1: Architecture Design (Agent A)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Design RESTful API endpoints
# - Plan authentication flow
# - Define error handling strategy
# - Fill "Architecture Design" section
# - Mark Task 1.1 complete
```

**Step 2: Database Schema (Agent B)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Design User and Task models
# - Define relationships
# - Plan indexes
# - Fill "Database Schema" section
# - Mark Task 1.2 complete
```

**Step 3: Project Setup (Agent C)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Haiku):
# - Create project directory structure
# - Set up requirements.txt
# - Create .env.example
# - Fill "Project Setup" section
# - Mark Task 1.3 complete
```

### Phase 2: Core Features (Parallel - ~20 min wall time)

**All 3 agents work simultaneously!**

**Agent D: Auth Module**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Implement registration and login
# - JWT token generation/validation
# - Password hashing
# - Create app/auth.py
# - Mark Task 2.1 complete
```

**Agent E: CRUD Module** (Different session!)
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Implement task CRUD endpoints
# - Create app/crud.py
# - Mark Task 2.2 complete
```

**Agent F: Models & Schemas** (Different session!)
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Haiku):
# - Implement SQLAlchemy models
# - Implement Pydantic schemas
# - Create app/main.py
# - Mark Task 2.3 complete
```

### Phase 3: Quality Assurance (Sequential with iteration - ~90 min)

**Step 1: Write Tests (Agent G)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Write comprehensive test suite
# - Auth tests, CRUD tests, integration tests
# - Ensure >90% coverage
# - Mark Task 3.1 complete
```

**Step 2: Code Review (Agent H)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Opus):
# - Review all code for security
# - Check error handling
# - Document findings
# - Mark Task 3.2 complete
```

**Step 3: Fix Issues (Agent I)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Sonnet):
# - Address review findings
# - Fix security issues
# - Improve error handling
# - Mark Task 3.3 complete
```

**Step 4: Final Review (Agent H)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Opus):
# - Verify all issues resolved
# - Run test suite
# - Approve for production
# - Mark Task 3.4 complete
```

### Phase 4: Documentation (Sequential - ~45 min)

**Step 1: API Documentation (Agent J)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Haiku):
# - Document all endpoints
# - Include examples
# - Create docs/API.md
# - Mark Task 4.1 complete
```

**Step 2: Deployment Guide (Agent K)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Haiku):
# - Write deployment instructions
# - Document environment variables
# - Create docs/DEPLOYMENT.md
# - Mark Task 4.2 complete
```

**Step 3: README (Agent L)**
```bash
make session PROJECT=examples/7-complex-application

# In AI interface (Haiku):
# - Write project overview
# - Quickstart guide
# - Create README.md
# - Set status: completed
```

## Expected Output

After completion, you'll have a complete application:

```
examples/7-complex-application/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with all routes
│   ├── models.py            # SQLAlchemy User and Task models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # Registration, login, JWT handling
│   ├── crud.py              # Task CRUD operations
│   ├── database.py          # DB connection and session
│   └── config.py            # Configuration management
├── tests/
│   ├── conftest.py          # Pytest fixtures
│   ├── test_auth.py         # Auth endpoint tests
│   ├── test_tasks.py        # CRUD endpoint tests
│   └── test_integration.py  # End-to-end flow tests
├── docs/
│   ├── API.md               # Complete API reference
│   └── DEPLOYMENT.md        # How to deploy
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
└── tasks.db                 # SQLite database (created on first run)
```

### Demo the Application

```bash
# 1. Navigate to project directory
cd examples/7-complex-application

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env: Set SECRET_KEY

# 4. Initialize database
python -c "from app.database import init_db; init_db()"

# 5. Run tests
pytest tests/ -v --cov=app
# Output: >90% coverage, all tests pass ✓

# 6. Start server
uvicorn app.main:app --reload

# 7. Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secure123"}'

# 8. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secure123"}'
# Returns: {"access_token": "eyJ...", "token_type": "bearer"}

# 9. Create a task (use token from step 8)
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"title": "Build Agent Hive example", "description": "Complete!"}'

# 10. View API docs
# Open browser: http://localhost:8000/docs
```

## Key Concepts Demonstrated

### 1. Mixed Execution Patterns

**Sequential** (Phase 1, 4):
- Design → Schema → Setup (order matters)
- API Docs → Deployment → README (builds on each other)

**Parallel** (Phase 2):
- Auth, CRUD, Models built simultaneously
- No coordination needed (different files)
- Wall time: max(D, E, F) instead of sum(D+E+F)

**Iterative** (Phase 3):
- Test → Review → Fix → Review (quality loop)
- May cycle multiple times

### 2. Real-World Development Workflow

This mirrors actual software teams:

```
Sprint 1: Architecture & Planning    (Foundation)
Sprint 2: Feature Development        (Parallel work)
Sprint 3: QA & Bug Fixes             (Review cycles)
Sprint 4: Release Preparation        (Documentation)
```

### 3. Agent Specialization

Match agent capabilities to task complexity:

| Task | Complexity | Model |
|------|------------|-------|
| Architecture Design | High | Sonnet/Opus |
| Database Schema | High | Sonnet |
| Project Setup | Low | Haiku |
| Auth Module | High | Sonnet |
| CRUD Module | Medium | Sonnet |
| Models/Schemas | Medium | Haiku/Sonnet |
| Testing | High | Sonnet |
| Code Review | Critical | Opus |
| Bug Fixes | Medium | Sonnet |
| Documentation | Low | Haiku |

Cost optimization: Use expensive models only where needed!

### 4. Quality Gates

Multiple checkpoints ensure quality:

```
Design Review → Implementation → Code Review → Testing →
Final Review → Documentation → Release
```

Can't skip stages!

### 5. Coordination Complexity

Agents must coordinate across patterns:

```yaml
# Phase 1: Sequential
owner: "claude-sonnet" (Agent A)
  ↓ completes
owner: null
  ↓ next agent starts
owner: "claude-sonnet" (Agent B)

# Phase 2: Parallel
# Three agents simultaneously:
Agent D note: "Working on auth module"
Agent E note: "Working on CRUD module"
Agent F note: "Working on models"

# Phase 3: Iterative
Review #1: "5 security issues found"
  ↓ Agent I fixes
Review #2: "All issues resolved ✓"
```

## Benefits of Complex Multi-Phase Pattern

### Realistic
- Mirrors real software development
- Includes all aspects: design, code, test, docs
- Shows how teams actually work

### Comprehensive Quality
- Multiple review points
- Specialized QA agents
- Test-driven development
- Security-first approach

### Efficient
- Parallel work where possible
- Sequential only when dependencies exist
- Optimal use of agent time

### Production-Ready
- Not just code, full deliverable
- Tests, docs, deployment guide
- Can actually be deployed!

## Variations to Try

### Different Application Types

**REST API** (This example):
- FastAPI, SQLAlchemy, JWT

**GraphQL API**:
- Use Strawberry or Graphene
- Similar phases, different implementation

**Web Application**:
- Add frontend (React, Vue)
- Parallel: Backend + Frontend teams

**CLI Tool**:
- Use Click or Typer
- Simpler than API, fewer phases

### Different Tech Stacks

**Node.js**:
- Express + MongoDB + Jest

**Go**:
- Gin + PostgreSQL + Go testing

**Rust**:
- Actix-web + Diesel + Cargo test

### Extended Features

Add more complexity:
- **Phase 2B**: Background jobs (Celery)
- **Phase 2C**: Caching (Redis)
- **Phase 2D**: Rate limiting
- **Phase 3B**: Load testing
- **Phase 3C**: Security scanning (Bandit)
- **Phase 4B**: Docker containerization
- **Phase 4C**: CI/CD pipeline

### Different Team Sizes

**Small Team** (6-8 agents):
- This example

**Large Team** (15-20 agents):
- More parallel work
- Specialized roles (frontend, backend, QA, DevOps)

**Minimal Team** (3-4 agents):
- Combine phases
- Less parallelization
- Longer timeline

## Real-World Applications

### SaaS Application
- User management
- Feature modules
- Billing integration
- Admin dashboard

### Internal Tool
- Data processing pipeline
- Reporting system
- Integration with existing systems

### Mobile Backend
- REST/GraphQL API
- Push notifications
- File upload handling
- Real-time features

### Microservice
- Single responsibility
- Service mesh integration
- Health checks, metrics
- Containerized deployment

## Troubleshooting

**Phase 2 agents conflict:**
- Ensure agents work on different files
- Auth (auth.py), CRUD (crud.py), Models (models.py)
- If conflicts, merge manually or run sequentially

**Tests fail after Phase 2:**
- Expected! Agent G writes tests for bugs
- Agent H reviews, Agent I fixes
- Tests should pass after Phase 3

**Code review finds major issues:**
- May need to revisit Phase 1 design
- Set blocked: true if architecture needs rework
- Escalate to human if fundamentally flawed

**Documentation doesn't match code:**
- Phase 4 agents must read actual code
- Don't just copy AGENCY.md design
- Verify by running demo script

**Too many agents needed:**
- Can combine tasks (e.g., one agent for all Phase 1)
- Reduce parallelization (run Phase 2 sequentially)
- Use same model for multiple phases

## Success Metrics

Track project completion:

```markdown
## Project Metrics

**Development**:
- Phases completed: 4/4 ✓
- Agents involved: 12
- Wall time: ~2.5 hours
- Agent time: ~4 hours

**Code Quality**:
- Test coverage: 94% ✓
- Security issues: 0 ✓
- Code review: Approved ✓
- Linting: Passed ✓

**Functionality**:
- Endpoints implemented: 7/7 ✓
- All tests passing: Yes ✓
- Demo script works: Yes ✓

**Documentation**:
- API docs: Complete ✓
- Deployment guide: Complete ✓
- README: Complete ✓
- Code comments: Adequate ✓

**Overall**: Production-ready! 🎉
```

## Next Steps

Once you've completed this example:

1. **Deploy it**: Follow DEPLOYMENT.md guide
2. **Extend it**: Add features (tags, priorities, due dates)
3. **Scale it**: Add more microservices
4. **Learn from it**: Study how agents coordinated
5. **Apply it**: Use patterns in your own projects

---

**Estimated time**: 2.5-4 hours (agent time), ~2-3 hours (wall time with parallelization)
**Difficulty**: Advanced
**Models required**: 12 agent assignments (can reuse same models)
**Learning value**: ⭐⭐⭐⭐⭐
**Production readiness**: Fully deployable
**Patterns demonstrated**: All of them!
