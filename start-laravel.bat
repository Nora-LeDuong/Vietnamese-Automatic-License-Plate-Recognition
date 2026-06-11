@echo off
cd /d "%~dp0laravel-app"

echo.
echo [Laravel] Starting server at http://127.0.0.1:8001
echo [Laravel] Upload limit: 512MB, Timeout: unlimited
echo [Laravel] Press Ctrl+C to stop
echo.

php -d upload_max_filesize=512M -d post_max_size=512M -d max_execution_time=0 -d max_input_time=0 -d memory_limit=1G -S 127.0.0.1:8001 -t public

pause
