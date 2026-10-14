@echo off
call :c .gitignore
call :c requirements.txt
call :c requirements-dev.txt
call :c pyproject.toml
call :c .env.example
call :c .env
call :c .github\workflows\ci.yml
call :c backend\alembic.ini
call :c backend\migrations\env.py
call :c backend\migrations\script.py.mako
call :c backend\app\__init__.py
call :c backend\app\config.py
call :c backend\app\database.py
call :c backend\app\models.py
call :c backend\app\schemas.py
call :c backend\app\security.py
call :c backend\app\deps.py
call :c backend\app\main.py
call :c backend\app\api\__init__.py
call :c backend\app\api\auth.py
call :c backend\tests\conftest.py
call :c backend\tests\test_auth.py
call :c backend\tests\test_config.py
call :c backend\tests\test_health.py
call :c backend\tests\test_migrations.py
exit /b
:c
if exist "%~1" (echo OK       %~1) else (echo MISSING  %~1)
exit /b