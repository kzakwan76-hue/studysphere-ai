# Development log

## Milestone 1: foundation and accounts
**Built:** project scaffold, settings, SQLAlchemy models, Alembic migrations, register/login/me, tests, CI.

**Decisions**
- Migrations from day one instead of `create_all`, with a test that checks migrations match the models.
- The app refuses to start with a `SECRET_KEY` shorter than 32 characters.
- Paths are computed from the file location, so commands work from any folder.

**Problems and fixes**
- (add yours here as they happen)