# Environment Configuration

This project uses two dedicated environment files.

## Files

```text
.env.dev   # Development environment (SQLite)
.env.prod  # Production environment (PostgreSQL)
```

## Switching Environment

The active environment is selected manually in `settings.py`.

```python
# Development
config = Config(RepositoryEnv(BASE_DIR / ".env.dev"))

# Production
# config = Config(RepositoryEnv(BASE_DIR / ".env.prod"))
```

Uncomment the desired configuration and comment out the other one before running the project.

## Database Mapping

| Environment | Database |
|------------|----------|
| `.env.dev` | SQLite |
| `.env.prod` | PostgreSQL |