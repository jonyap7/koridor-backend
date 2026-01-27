# Partimer Backend API

WhatsApp-First Part-Time Worker Lead Marketplace Backend

## Overview

Partimer is a lead marketplace platform that connects employers with part-time workers. The platform follows a lead-based business model where:
- Workers register and set their availability
- Employers post job requirements  
- The system matches jobs to workers based on location, availability, and skills
- Workers receive job offers and can accept/reject
- Employers pay to unlock contact details of workers who accepted (the "lead")

## Tech Stack

- **Framework**: FastAPI (Python 3.12)
- **Database**: SQLAlchemy (supports PostgreSQL/SQLite)
- **Validation**: Pydantic v2
- **Authentication**: Bearer token-based (production should use JWT)

## Architecture

### Role-Based Routes

The API is organized by user role with strict access control:

```
/api/auth/*          - Authentication endpoints (public)
/api/workers/*       - Worker-specific endpoints (requires WORKER role)
/api/employers/*     - Employer-specific endpoints (requires EMPLOYER role)
/api/admin/*         - Admin-specific endpoints (requires ADMIN role)
/api/matching/*      - Matching algorithm triggers
```

### Data Model

**Core Entities:**
- `User` - Base user account (role: worker/employer/admin)
- `Worker` - Worker profile with skills, availability, location
- `WorkerAvailability` - Weekly schedule slots
- `Employer` - Employer profile with company details
- `Job` - Job posting with requirements and timing
- `JobMatch` - The core "lead" product (worker matched to job)
- `Payment` - Payment records for purchased leads
- `AdminActionLog` - Audit trail

### Business Rules

1. **Role Separation**: Each role has completely separate routes and data access
2. **Lead-Based Payment**: Payment only unlocks contact details, not labor
3. **Salary is Informational**: Displayed to workers but not part of payment model
4. **Status Management**: All entities have status workflows with guards
5. **Matching Algorithm**: Considers location (haversine), availability overlap, skills, experience
6. **Response Deadlines**: Workers must respond within configured timeframe
7. **One Payment Per Lead**: Contact details locked until payment, then permanently unlocked

## API Endpoints

### Authentication

```
POST   /api/auth/register/worker      - Worker registration (phone-based)
POST   /api/auth/register/employer    - Employer registration (email/password)
POST   /api/auth/login                - Login (role-specific)
GET    /api/auth/me                   - Get current user info
POST   /api/auth/logout               - Logout and invalidate token
```

### Workers

```
GET    /api/workers/profile           - Get own profile
PUT    /api/workers/profile           - Update profile
GET    /api/workers/availability      - List availability slots
POST   /api/workers/availability      - Add availability slot
DELETE /api/workers/availability/{id} - Remove slot
GET    /api/workers/offers            - List job offers
POST   /api/workers/offers/{id}/respond - Accept/reject offer
GET    /api/workers/dashboard         - Dashboard statistics
```

### Employers

```
GET    /api/employers/profile         - Get own profile
PUT    /api/employers/profile         - Update profile
GET    /api/employers/jobs            - List own jobs
POST   /api/employers/jobs            - Create job
GET    /api/employers/jobs/{id}       - Get job details
PUT    /api/employers/jobs/{id}       - Update job
DELETE /api/employers/jobs/{id}       - Cancel job
POST   /api/employers/jobs/{id}/publish - Publish job to start matching
GET    /api/employers/jobs/{id}/matches - List matches (without contact details)
POST   /api/employers/matches/{id}/unlock - Pay and unlock contact details
GET    /api/employers/dashboard       - Dashboard statistics
```

### Admin

```
GET    /api/admin/workers             - List all workers
GET    /api/admin/workers/{id}        - Get worker details
POST   /api/admin/workers/{id}/action - Activate/suspend/verify worker
GET    /api/admin/employers           - List all employers
GET    /api/admin/employers/{id}      - Get employer details
POST   /api/admin/employers/{id}/action - Activate/suspend/restrict employer
GET    /api/admin/jobs                - List all jobs
POST   /api/admin/jobs/{id}/action    - Cancel/reopen job
GET    /api/admin/logs                - View audit logs
GET    /api/admin/stats               - System-wide statistics
```

### Matching

```
POST   /api/matching/jobs/{id}/trigger - Manually trigger matching for a job
POST   /api/matching/expire-matches    - Expire old matches (admin only)
```

## Setup

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional, defaults provided)
cp .env.example .env
# Edit .env with your DATABASE_URL if using PostgreSQL
```

### Database Migration

The database schema is automatically created on startup via SQLAlchemy:

```python
from app.db import Base, engine
Base.metadata.create_all(bind=engine)
```

### Running the Server

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
docker build -t partimer-backend .
docker run -p 8000:8000 partimer-backend
```

## Configuration

Edit `app/core/settings.py` or set environment variables:

- `DATABASE_URL` - Database connection string (default: SQLite)
- `BACKEND_CORS_ORIGINS` - Allowed CORS origins
- `SECRET_KEY` - Secret key for token generation
- `WHATSAPP_API_URL` - WhatsApp Business API endpoint (Phase 10)
- `WHATSAPP_API_TOKEN` - WhatsApp API token (Phase 10)
- `STRIPE_SECRET_KEY` - Stripe payment key (Phase 11)

## Testing

Basic API test:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

Comprehensive test script is available in the repository.

## Development Status

### Completed Phases

- ✅ Phase 0-2: System foundation and architecture design
- ✅ Phase 3: Database schema (PostgreSQL-compatible)
- ✅ Phase 4: Backend API contract
- ✅ Phase 7: Authentication with role enforcement
- ✅ Phase 8: Core data wiring (CRUD operations)
- ✅ Phase 9: Matching logic (availability, location, skills)

### Pending Phases

- ⏳ Phase 10: WhatsApp Business API integration
- ⏳ Phase 11: Payment gateway integration (Stripe)
- ⏳ Phase 12: Enhanced admin controls
- ⏳ Phase 13: QA, abuse prevention, launch readiness

## Security Considerations

### Current Implementation (Development)

- Simple token-based auth (in-memory storage)
- SHA256 password hashing
- Basic role-based access control

### Production Requirements

- [ ] Use JWT with proper secret management
- [ ] Use bcrypt/argon2 for password hashing
- [ ] Store tokens in Redis with TTL
- [ ] Add rate limiting
- [ ] Add request validation and sanitization
- [ ] Enable HTTPS only
- [ ] Add CSRF protection
- [ ] Implement proper session management
- [ ] Add logging and monitoring
- [ ] Regular security audits

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.
