@echo off
echo ===== files =====
call :c .gitignore
call :c requirements.txt
call :c requirements-dev.txt
call :c pyproject.toml
call :c .env
call :c .github\workflows\ci.yml
call :c backend\alembic.ini
call :c backend\migrations\env.py
call :c backend\app\config.py
call :c backend\app\models.py
call :c backend\app\schemas.py
call :c backend\app\main.py
call :c backend\app\api\auth.py
call :c backend\app\api\documents.py
call :c backend\app\api\search.py
call :c backend\app\services\throttle.py
call :c backend\app\retrieval\__init__.py
call :c backend\app\retrieval\tokenizer.py
call :c backend\app\retrieval\bm25.py
call :c backend\app\retrieval\ranking.py
call :c backend\app\retrieval\search.py
call :c backend\app\retrieval\evaluation.py
call :c backend\tests\test_tokenizer.py
call :c backend\tests\test_bm25.py
call :c backend\tests\test_ranking.py
call :c backend\tests\test_search_api.py
call :c backend\tests\test_retrieval_eval.py
call :c sample_docs\binary_search.md
call :c sample_docs\tcp_handshake.md
call :c sample_docs\photosynthesis.md
call :c sample_docs\sorting_algorithms.md
call :c sample_docs\ohms_law.md
call :c eval\retrieval_questions.json
call :c scripts\eval_retrieval.py
echo.
echo ===== edited files contain the new code =====
call :h "class SearchResponse" backend\app\schemas.py
call :h "search.router" backend\app\main.py
exit /b

:c
if exist "%~1" (echo OK       %~1) else (echo MISSING  %~1)
exit /b

:h
findstr /c:%1 %2 >nul 2>&1 && (echo OK       %~2 has %~1) || (echo MISSING  %~2 lacks %~1)
exit /b