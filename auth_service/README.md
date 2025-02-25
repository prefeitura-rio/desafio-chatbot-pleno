# Authentication Service

This is the Authentication Service for the Carioca Digital chatbot, providing user authentication, registration, and session management.

## Features

- User registration and login
- JWT-based authentication with OAuth2-compatible endpoint
- Refresh token management
- Session tracking
- Rate limiting
- User profile management

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis

### Environment Variables

Create a `.env` file in the `auth_service` directory with the following variables:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/chatdb
REDIS_URI=redis://redis:6379/0
JWT_SECRET=your_jwt_secret_key_at_least_32_chars_long
DEBUG=True
```

### Running with Docker

The authentication service is designed to run as part of the docker-compose setup:

```bash
docker-compose up -d
```

This will start the service along with PostgreSQL and Redis.

### Running Locally (Development)

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run database migrations:

```bash
alembic upgrade head
```

4. Start the service:

```bash
uvicorn app.main:app --reload
```

## API Documentation

When running in debug mode, API documentation is available at:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## API Endpoints

### Authentication

- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login and get access token
- `POST /api/v1/auth/login/oauth`: OAuth2 compatible login
- `POST /api/v1/auth/refresh`: Refresh access token
- `POST /api/v1/auth/logout`: Logout from current session

### Users

- `GET /api/v1/users/me`: Get current user info
- `PUT /api/v1/users/me`: Update current user info
- `GET /api/v1/users/{user_id}`: Get user by ID (admin only)
- `PUT /api/v1/users/{user_id}`: Update user by ID (admin only) 