@echo off
<<<<<<< HEAD
title VALPR - Web Frontend (Laravel)

cd /d "%~dp0laravel-app"

echo ================================================================
echo       VALPR - KHOI DONG FRONTEND WEB (PHP Laravel)
echo ================================================================
echo.

REM 1. Kiem tra PHP
where php >nul 2>nul
if %errorlevel% neq 0 goto NO_PHP

REM 2. Kiem tra file .env
if not exist ".env" (
    echo [INFO] Chua co file .env, dang sao chep tu .env.example...
    copy .env.example .env >nul
)

REM 3. Kiem tra thu vien Composer
if exist "vendor\autoload.php" goto CHECK_KEY
where composer >nul 2>nul
if %errorlevel% neq 0 goto NO_COMPOSER
echo [INFO] Phat hien lan dau chay: Dang cai dat dependencies qua Composer...
call composer install --no-interaction
if %errorlevel% neq 0 goto COMPOSER_FAIL

:CHECK_KEY
REM 4. Kiem tra APP_KEY
php -r "exit(file_exists('.env') && preg_match('/^APP_KEY=base64:/m', file_get_contents('.env')) ? 0 : 1);" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Dang sinh khoa bao mat ung dung [APP_KEY]...
    call php artisan key:generate --force
)

REM 5. Kiem tra SQLite Database va chay Migrations
if not exist "database\database.sqlite" (
    echo [INFO] Dang khoi tao file co so du lieu database.sqlite...
    type nul > "database\database.sqlite"
)
call php artisan migrate --force

REM 6. Kiem tra Storage Symbolic Link
if not exist "public\storage" (
    echo [INFO] Dang tao storage link...
    call php artisan storage:link
)

REM 7. Kiem tra Frontend Assets [public/build]
if exist "public\build" goto CLEAR_VIEW
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [CANH BAO] Khong tim thay Node/NPM. Neu giao dien thieu CSS/JS, hay cai Node.js va chay 'npm run build'.
    goto CLEAR_VIEW
)
echo [INFO] Dang cai dat NPM packages va build giao dien...
call npm install
call npm run build

:CLEAR_VIEW
call php artisan view:clear >nul 2>nul

echo.
echo ================================================================
echo  [Laravel Web] Server dang chay tai:   http://127.0.0.1:8001
echo  [Laravel Web] Gioi han upload:        512MB
echo  [Laravel Web] Nhan Ctrl+C de dung server.
echo ================================================================
echo.

php -d upload_max_filesize=512M -d post_max_size=512M -d max_execution_time=0 -d max_input_time=0 -d memory_limit=1G -S 127.0.0.1:8001 -t public
goto END

:NO_PHP
echo [LOI] Khong tim thay PHP tren he thong [chua cai hoac chua them vao PATH].
echo Vui long cai dat PHP 8.2 tro len va them vao bien moi truong PATH.
pause
exit /b 1

:NO_COMPOSER
echo [LOI] Khong tim thay Composer tren he thong.
echo Vui long cai dat Composer tai https://getcomposer.org/
pause
exit /b 1

:COMPOSER_FAIL
echo [LOI] 'composer install' that bai.
pause
exit /b 1

:END
=======
cd /d "%~dp0laravel-app"

echo.
echo [Laravel] Starting server at http://127.0.0.1:8001
echo [Laravel] Upload limit: 512MB, Timeout: unlimited
echo [Laravel] Press Ctrl+C to stop
echo.

php -d upload_max_filesize=512M -d post_max_size=512M -d max_execution_time=0 -d max_input_time=0 -d memory_limit=1G -S 127.0.0.1:8001 -t public

>>>>>>> 8ae3a766e952d482da778e3de7378e402743d3dd
pause
