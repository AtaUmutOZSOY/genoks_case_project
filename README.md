# Multi-Tenant Django REST API

A schema-based multi-tenant Django REST API system with PostgreSQL. Each "Center" gets its own database schema ensuring complete data isolation between tenants.

## Architecture Overview

- **Multi-Tenancy Model**: Schema-based isolation
- **Database**: PostgreSQL with one database, multiple schemas per tenant
- **Backend**: Django REST Framework
- **Containerization**: Docker & Docker Compose

## Database Design

### Public Schema (Shared)
- `public.centers` - Tenant registry
- `public.users` - Shared user management

### Tenant Schemas (Per Center)
- `center_{tenant_id}.samples` - Tenant-specific sample data

## Data Models

### BaseModel (Abstract)
All models inherit from BaseModel which provides:
- `id`: UUID Primary Key
- `created_at`, `updated_at`: Timestamps
- `is_active`: Soft delete flag
- `created_by`, `updated_by`: Audit trail

### Center Model (Public Schema)
```python
- name: String (unique)
- schema_name: String (unique)
- description: Text (optional)
- settings: JSONField (center-specific configs)
```

### User Model (Public Schema)
```python
- username: String (unique)
- email: String (unique)
- first_name, last_name: String
- phone: String (optional)
- center: Foreign Key to Center
- role: String (admin, user, viewer)
```

### Sample Model (Tenant Schema)
```python
- name: String
- description: Text (optional)
- sample_type: String (blood, urine, tissue, etc.)
- status: String (pending, processing, completed, rejected, archived)
- barcode: String (unique within tenant)
- user_id: Integer (references public.users.id)
- metadata: JSONField (flexible data)
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/AtaUmutOZSOY/genoks_case_project.git
cd genoks_case_project
```

2. **Start the services**
```bash
docker compose up -d
```

3. **Verify container status**
```bash
docker compose ps
```

4. **Create a superuser (optional)**
```bash
docker compose exec web python manage.py createsuperuser
```

### Available Services

- **API & Interactive Documentation**: http://localhost:8000 (auto-redirects to Swagger UI)
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **ReDoc Documentation**: http://localhost:8000/api/redoc/
- **Database**: PostgreSQL on port 5432
- **Redis**: Redis on port 6379

## Authentication

The API uses Token-based authentication. All endpoints (except authentication endpoints) require authentication.

### Authentication Endpoints
```
POST   /api/auth/login/                 # Login and get API token
POST   /api/auth/logout/                # Logout and invalidate token
GET    /api/auth/user/                  # Get current user info
POST   /api/auth/create-superuser/      # Create superuser (initial setup)
```

### Usage

#### Command Line (curl)
1. **Get Token**: Use `/api/auth/login/` with username/password
2. **Use Token**: Include in header: `Authorization: Token your-token-here`

#### Swagger UI Integration
1. **Access Swagger**: Visit http://localhost:8000
2. **Login**: Use `/api/auth/login/` endpoint to get your token
3. **Authorize**: 
   - Click the **"Authorize"** button (🔒) at the top right
   - In the **tokenAuth** section, enter: `Token your-actual-token-here`
   - Click **"Authorize"** then **"Close"**
4. **Test APIs**: Now all endpoints are authenticated and ready to use

**Example Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

**Response:**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 1,
  "username": "admin",
  "message": "Login successful"
}
```

## API Endpoints

### Centers Management
```
POST   /api/centers/                    # Create new center
GET    /api/centers/                    # List all centers
GET    /api/centers/{id}/               # Get center details
PUT    /api/centers/{id}/               # Update center
DELETE /api/centers/{id}/               # Soft delete center

# Additional actions
POST   /api/centers/{id}/restore/       # Restore soft deleted center
DELETE /api/centers/{id}/hard_delete/   # Permanently delete center
GET    /api/centers/{id}/stats/         # Get center statistics
GET    /api/centers/summary/            # Get centers summary
```

### User Management
```
POST   /api/users/                      # Create user
GET    /api/users/                      # List users
GET    /api/users/{id}/                 # Get user details
PUT    /api/users/{id}/                 # Update user
DELETE /api/users/{id}/                 # Soft delete user

# Additional actions
POST   /api/users/{id}/change_center/   # Change user's center
POST   /api/users/{id}/change_role/     # Change user's role
GET    /api/users/by_center/{center_id}/ # Get users by center
GET    /api/users/summary/              # Get users summary
```

### Sample Management (Tenant-Specific)
```
POST   /api/centers/{center_id}/samples/       # Create sample
GET    /api/centers/{center_id}/samples/       # List samples
GET    /api/centers/{center_id}/samples/{id}/  # Get sample details
PUT    /api/centers/{center_id}/samples/{id}/  # Update sample
DELETE /api/centers/{center_id}/samples/{id}/  # Soft delete sample

# Additional actions
POST   /api/centers/{center_id}/samples/{id}/process/        # Start processing
POST   /api/centers/{center_id}/samples/{id}/complete/       # Complete processing
POST   /api/centers/{center_id}/samples/{id}/reject/         # Reject sample
POST   /api/centers/{center_id}/samples/{id}/archive/        # Archive sample
GET    /api/centers/{center_id}/samples/by_barcode/{barcode}/ # Find by barcode
GET    /api/centers/{center_id}/samples/by_status/{status}/   # Filter by status
GET    /api/centers/{center_id}/samples/stats/               # Get sample statistics
```

## Development

### Project Structure
```
genoks_case_project/
├── apps/
│   ├── centers/         # Center management
│   ├── users/           # User management
│   ├── samples/         # Sample management (tenant-specific)
│   └── common/          # Shared utilities
├── config/
│   └── settings/        # Django settings
├── middleware/          # Custom middleware
├── utils/               # Utility functions
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Environment Configuration

The application uses environment variables defined in `docker-compose.yml`:

```yaml
- SECRET_KEY=django-insecure-change-this-in-production-2025
- DEBUG=True
- DATABASE_URL=postgres://postgres:postgres@db:5432/multitenant_db
- REDIS_URL=redis://redis:6379/0
- ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,web
```

### Management Commands

```bash
# Access Django shell
docker compose exec web python manage.py shell

# Run migrations
docker compose exec web python manage.py migrate

# Create migrations
docker compose exec web python manage.py makemigrations

# Access container shell
docker compose exec web sh

# View logs
docker compose logs web
docker compose logs -f web  # Follow logs
```

## Multi-Tenant Features

### Schema Management
- **Dynamic Schema Creation**: Automatically creates new schema when a center is created
- **Schema Naming**: Uses format `center_{tenant_id}` (UUIDs with hyphens removed)
- **Migration Management**: Runs migrations for each tenant schema
- **Complete Isolation**: Each tenant's data is completely separated

### Tenant Resolution
- **URL-based**: Extract tenant info from URL path (`/api/centers/{center_id}/samples/`)
- **Middleware**: Custom middleware sets database schema context
- **Context Managers**: Switch between schemas programmatically

### Usage Example

```python
from utils.tenant_utils import set_tenant_schema_context
from apps.samples.models import Sample

# Switch to tenant schema
with set_tenant_schema_context('center_123'):
    samples = Sample.objects.all()  # Only samples from this tenant
```

## Administration

### Django Admin Interface
- **URL**: http://localhost:8000/admin/
- **Features**: Manage centers, users, and view statistics
- **Bulk Actions**: Activate/deactivate users, change roles

### Database Access
```bash
# Connect to PostgreSQL
docker compose exec db psql -U postgres -d multitenant_db

# List schemas
\dn

# Switch to tenant schema
SET search_path TO center_123, public;
```

## Testing

### Quick Start Testing

1. **Create Superuser** (for initial setup):
```bash
curl -X POST http://localhost:8000/api/auth/create-superuser/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123", "email": "admin@example.com"}'
```

2. **Login and Get Token**:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

3. **Use API with Token**:
```bash
# Test centers endpoint (with authentication)
curl -X GET http://localhost:8000/api/centers/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your-token-here"

# Create a center
curl -X POST http://localhost:8000/api/centers/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your-token-here" \
  -d '{"name": "Test Center", "description": "Test center description"}'
```

### Interactive Testing with Swagger UI

**Step-by-Step Guide:**

1. **Open Browser**: Navigate to http://localhost:8000
2. **Create/Login User**:
   - First time: Use `POST /api/auth/create-superuser/` 
   - Existing user: Use `POST /api/auth/login/`
3. **Copy Token**: From the login response, copy the token value
4. **Authorize in Swagger**:
   ```
   📌 Click "Authorize" button (🔒 icon) at top right
   📌 In "tokenAuth" field, enter: Token your-token-here
   📌 Click "Authorize" → "Close"
   ```
5. **Test APIs**: All endpoints now work with authentication

**⚠️ Important Token Format:**
```
✅ Correct:   Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
❌ Wrong:     9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
❌ Wrong:     Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```
**Must include "Token " prefix with space!**

### Interactive API Documentation

- **Primary Interface**: http://localhost:8000 (automatically redirects to Swagger UI)
- **Full Documentation**: Comprehensive interactive API documentation with authentication
- **Test Environment**: Built-in testing interface for all endpoints
- **Authentication Integration**: Seamless token-based authentication in browser

## Production Deployment

### Environment Configuration
1. Set `DEBUG=False`
2. Use strong `SECRET_KEY`
3. Configure proper `ALLOWED_HOSTS`
4. Set up production database
5. Configure Redis for caching
6. Set up SSL/HTTPS

### Security Considerations
- **Schema Isolation**: Complete data separation between tenants
- **Input Validation**: Comprehensive validation on all inputs
- **Access Control**: Role-based permissions per tenant
- **Audit Trail**: Built-in audit fields in BaseModel

## Technology Stack

- **Django 4.2+**: Web framework
- **Django REST Framework**: API framework with Token authentication
- **PostgreSQL 15**: Database with schema-based multi-tenancy
- **Redis 7**: Caching and session storage
- **Docker**: Containerization
- **psycopg2**: PostgreSQL adapter
- **drf-spectacular**: Interactive API documentation (Swagger UI)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This is a case study implementation for multi-tenant Django REST API with schema-based isolation. Modify according to your specific requirements before production use.