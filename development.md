# Project Development Guide

This guide explains how to set up the local development environment from scratch using Docker (for the database) and Alembic (for database schema migrations).

### Prerequisites
- Python 3.10+
- Docker Desktop installed and running
- A `.env` file populated with your credentials:
  ```
  DATABASE_URL=postgresql+asyncpg://postgres:root@localhost:5433/profile_chatbot_local
  OPENAI_API_KEY="..."
  # other AWS variables...
  ```

---

## 1. Start the Database
We use Docker exclusively to spin up a raw PostgreSQL 16 container equipped with the `pgvector` extension.

```powershell
docker compose up -d
```
*Note: This binds to port `5433` on your host machine to prevent conflicts with any native Windows PostgreSQL installations.*

## 2. Enable pgvector
Before we can create our tables, we must manually create the `vector` extension inside the database. This only needs to be run **once** per completely fresh database volume.

```powershell
docker exec -i pgvector_db psql -U postgres -d profile_chatbot_local -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 3. Apply Schema Migrations
We use **Alembic** to manage our tables. This looks at `app.database.models` and creates any missing tables or columns. This mirrors exactly how the production AWS RDS database will be initialized.

```powershell
alembic upgrade head
```

## 4. Run the API
Activate your virtual environment and start the FastAPI server:

```powershell
.\venv\Scripts\activate
uvicorn app.main:app --reload
```
The API runs at `http://127.0.0.1:8000`.

---

## Modifying the Database Schema
When you need to add a new table or column in the future:
1. Update your Python classes in `app/database/models.py`.
2. Generate a new migration script:
   ```powershell
   alembic revision --autogenerate -m "description of change"
   ```
3. Look at the generated file in `alembic/versions/` (Ensure it accurately added `import pgvector` if modifying vector columns).
4. Apply to your local database:
   ```powershell
   alembic upgrade head
   ```

## Nuke & Rebuild (Resetting completely)
If your database gets corrupted locally, you can easily wipe the entire database volume and start over:
```powershell
docker compose down -v
docker compose up -d
docker exec -i pgvector_db psql -U postgres -d profile_chatbot_local -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic upgrade head
```
