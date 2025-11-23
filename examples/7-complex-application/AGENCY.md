---
project_id: complex-application-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: high
tags: [example, complex, full-stack, comprehensive, tutorial]
---

# Complex Application Example: Task Management API

## Objective
Demonstrate a comprehensive full-stack development workflow that combines multiple Agent Hive patterns (sequential, parallel, review cycles) to build a production-ready RESTful API application.

**Project**: Build a Task Management API with authentication, CRUD operations, and comprehensive testing.

## Tech Stack

- **Backend**: Python FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Auth**: JWT tokens
- **Testing**: pytest
- **Documentation**: OpenAPI/Swagger (auto-generated)

## Project Structure

```
app/
├── main.py              # FastAPI application
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── auth.py              # Authentication logic
├── crud.py              # Database operations
├── database.py          # Database connection
└── config.py            # Configuration
tests/
├── test_auth.py         # Auth tests
├── test_tasks.py        # Task CRUD tests
├── test_integration.py  # End-to-end tests
└── conftest.py          # Test fixtures
docs/
├── API.md               # API documentation
└── DEPLOYMENT.md        # Deployment guide
.env.example             # Environment template
requirements.txt         # Dependencies
README.md                # Project overview
```

## Development Phases

### 🏗️ Phase 1: Foundation (Sequential)
```
Architecture Design → Database Schema → Project Setup
      (A)                  (B)              (C)
```

### 🔨 Phase 2: Core Features (Parallel)
```
     ┌─ Auth Module (D) ─────┐
     │                       │
Setup┤─ CRUD Module (E) ─────┤→ Integration
     │                       │
     └─ Models/Schemas (F) ──┘
```

### ✅ Phase 3: Quality Assurance (Review Pipeline)
```
Write Tests → Code Review → Fix Issues → Final Review
    (G)          (H)           (I)          (H)
```

### 📚 Phase 4: Documentation (Sequential)
```
API Docs → Deployment Guide → README
   (J)          (K)             (L)
```

## Detailed Tasks

---

## Phase 1: Foundation

### Task 1.1: Architecture Design (Agent A - Architect)
- [ ] Design API endpoints (RESTful structure)
- [ ] Define data models (User, Task)
- [ ] Plan authentication flow (JWT)
- [ ] Design error handling strategy
- [ ] Document in "Architecture Design" section

### Task 1.2: Database Schema (Agent B - Database Designer)
- [ ] Design User model (id, username, password_hash, created_at)
- [ ] Design Task model (id, title, description, status, user_id, created_at, updated_at)
- [ ] Define relationships (User has many Tasks)
- [ ] Plan indexes for performance
- [ ] Document in "Database Schema" section

### Task 1.3: Project Setup (Agent C - DevOps)
- [ ] Create project structure (directories, files)
- [ ] Set up requirements.txt (FastAPI, SQLAlchemy, PyJWT, pytest)
- [ ] Create .env.example
- [ ] Set up database configuration
- [ ] Document in "Project Setup" section

---

## Phase 2: Core Features (Parallel - 3 agents work simultaneously)

### Task 2.1: Auth Module (Agent D)
- [ ] Implement user registration endpoint
- [ ] Implement login endpoint (returns JWT)
- [ ] Implement password hashing (bcrypt)
- [ ] Implement JWT token generation/validation
- [ ] Create `app/auth.py`

### Task 2.2: CRUD Module (Agent E)
- [ ] Implement create task endpoint
- [ ] Implement read task(s) endpoint
- [ ] Implement update task endpoint
- [ ] Implement delete task endpoint
- [ ] Create `app/crud.py`

### Task 2.3: Models & Schemas (Agent F)
- [ ] Implement SQLAlchemy models (`app/models.py`)
- [ ] Implement Pydantic schemas (`app/schemas.py`)
- [ ] Set up database connection (`app/database.py`)
- [ ] Create main FastAPI app (`app/main.py`)
- [ ] Implement config (`app/config.py`)

---

## Phase 3: Quality Assurance (Review Pipeline)

### Task 3.1: Write Tests (Agent G - Test Engineer)
- [ ] Write auth tests (registration, login, invalid credentials)
- [ ] Write CRUD tests (create, read, update, delete tasks)
- [ ] Write integration tests (full user flows)
- [ ] Ensure >90% code coverage
- [ ] Create all test files

### Task 3.2: Code Review (Agent H - Senior Developer)
- [ ] Review all code for security issues
- [ ] Check error handling
- [ ] Verify JWT implementation is secure
- [ ] Check SQL injection prevention
- [ ] Document findings in "Code Review Findings"

### Task 3.3: Fix Issues (Agent I - Developer)
- [ ] Address all code review findings
- [ ] Improve error handling
- [ ] Add input validation
- [ ] Fix security issues
- [ ] Update tests as needed

### Task 3.4: Final Review (Agent H - Senior Developer)
- [ ] Verify all issues resolved
- [ ] Run full test suite
- [ ] Approve for documentation
- [ ] Mark code as production-ready

---

## Phase 4: Documentation (Sequential)

### Task 4.1: API Documentation (Agent J)
- [ ] Document all endpoints (method, path, params, responses)
- [ ] Include example requests/responses
- [ ] Document authentication flow
- [ ] Create `docs/API.md`

### Task 4.2: Deployment Guide (Agent K)
- [ ] Write deployment instructions
- [ ] Document environment variables
- [ ] Include production considerations
- [ ] Create `docs/DEPLOYMENT.md`

### Task 4.3: README (Agent L)
- [ ] Write project overview
- [ ] Include quickstart guide
- [ ] Document development setup
- [ ] Add testing instructions
- [ ] Create `README.md`

---

## Design Documentation

### Architecture Design
<!-- Agent A: Document architecture here -->

**API Endpoints**:
```
POST   /auth/register    - Register new user
POST   /auth/login       - Login and get JWT token
GET    /tasks            - Get all tasks (authenticated)
POST   /tasks            - Create task (authenticated)
GET    /tasks/{id}       - Get specific task (authenticated)
PUT    /tasks/{id}       - Update task (authenticated)
DELETE /tasks/{id}       - Delete task (authenticated)
```

**Authentication Flow**:


**Error Handling**:


---

### Database Schema
<!-- Agent B: Document schema here -->

**User Model**:
```python
id: Integer, Primary Key
username: String(50), Unique, Not Null
password_hash: String(255), Not Null
created_at: DateTime, Default Now
```

**Task Model**:
```python
id: Integer, Primary Key
title: String(100), Not Null
description: Text, Nullable
status: String(20), Default "pending"
user_id: Integer, Foreign Key → users.id
created_at: DateTime, Default Now
updated_at: DateTime, Default Now, OnUpdate Now
```

**Relationships**:


**Indexes**:


---

### Project Setup
<!-- Agent C: Document setup here -->

**Dependencies**:


**Environment Variables**:


**Database Initialization**:


---

## Code Review Findings

### Review #1 (After Phase 2)
<!-- Agent H: Document initial findings -->

**Security Issues**:
-

**Code Quality**:
-

**Error Handling**:
-

**Required Changes**:
-

---

### Review #2 (Final)
<!-- Agent H: Final review -->

**Status**: [ ] APPROVED / [ ] NEEDS MORE WORK

**Verification**:
- [ ] All security issues resolved
- [ ] Error handling comprehensive
- [ ] Tests pass and coverage >90%
- [ ] Code follows best practices

---

## Agent Coordination Notes

### Phase 1 (Sequential)
- Agent A → Agent B → Agent C (strict order)
- Each agent must complete before next starts

### Phase 2 (Parallel)
- Agents D, E, F work **simultaneously**
- Each works on different files (no conflicts)
- All three must complete before Phase 3

### Phase 3 (Review Pipeline)
- Agent G → Agent H → Agent I → Agent H (sequential with iteration)
- May loop if issues found

### Phase 4 (Sequential)
- Agent J → Agent K → Agent L (strict order)
- Documentation builds on code

---

## Agent Notes
<!-- Add timestamped notes as you work -->

---

## Success Criteria

Application is complete when:
- ✅ All endpoints implemented and tested
- ✅ Authentication works securely (JWT)
- ✅ CRUD operations function correctly
- ✅ Test coverage >90%
- ✅ No security vulnerabilities
- ✅ Code review approved
- ✅ Complete documentation
- ✅ Application runs and can be demoed

## Demo Script

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up database
python -c "from app.database import init_db; init_db()"

# 3. Run tests
pytest tests/ -v --cov=app

# 4. Start server
uvicorn app.main:app --reload

# 5. Test endpoints
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# 6. View API docs
# Open browser: http://localhost:8000/docs
```

---

## Estimated Effort

- **Phase 1**: 30-45 minutes (3 agents sequential)
- **Phase 2**: 45-60 minutes (3 agents parallel = ~20 min wall time)
- **Phase 3**: 60-90 minutes (review cycles)
- **Phase 4**: 30-45 minutes (3 agents sequential)

**Total**: 2.5-4 hours agent time, ~2-3 hours wall time with parallelization

---

## Learning Outcomes

This comprehensive example teaches:
1. **Sequential coordination**: Architecture → Schema → Setup
2. **Parallel execution**: Multiple modules simultaneously
3. **Review workflows**: Iterative quality improvement
4. **Specialization**: Different agents for different skills
5. **Production readiness**: Security, testing, documentation
6. **Real-world patterns**: How actual development teams work
