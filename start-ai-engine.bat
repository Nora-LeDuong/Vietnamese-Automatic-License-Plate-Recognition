@echo off
<<<<<<< HEAD
title VALPR - AI Engine (FastAPI)

cd /d "%~dp0ai-engine"

echo ================================================================
echo       VALPR - KHOI DONG BACKEND AI ENGINE (FastAPI)
echo ================================================================
echo.

REM 1. Kiem tra Python tren he thong
where python >nul 2>nul
if %errorlevel% neq 0 goto NO_PYTHON

REM 2. Kiem tra va Kich hoat moi truong ao .venv
if exist ".venv\Scripts\activate.bat" goto USE_VENV

REM Kiem tra xem moi truong Python he thong da co day du thu vien chua
python -c "import fastapi, uvicorn, ultralytics, cv2, torch, imageio_ffmpeg" >nul 2>nul
if %errorlevel% equ 0 goto USE_SYSTEM_PYTHON

REM 3. Khoi tao .venv moi vi chua co thu vien
echo [INFO] Phat hien lan dau chay: Chua co moi truong ao hoac thieu thu vien can thiet.
echo [INFO] Dang tu dong tao moi truong ao .venv...
python -m venv .venv
if %errorlevel% neq 0 goto VENV_FAIL

call .venv\Scripts\activate.bat
echo [INFO] Dang cai dat cac thu vien can thiet tu requirements.txt...
echo       Vui long doi trong it phut de tai PyTorch va YOLO...
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if %errorlevel% neq 0 goto PIP_FAIL
echo [INFO] Da cai dat day du cac thu vien AI!
goto RUN_SERVER

:USE_VENV
call .venv\Scripts\activate.bat
python -c "import fastapi, uvicorn, ultralytics, cv2, torch, imageio_ffmpeg" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Dang kiem tra va cai dat bo sung dependencies vao .venv...
    pip install -r requirements.txt
)
goto RUN_SERVER

:USE_SYSTEM_PYTHON
echo [INFO] Su dung moi truong Python he thong [da co day du thu vien can thiet].
goto RUN_SERVER

:RUN_SERVER
REM Dam bao thu muc tam ton tai
if not exist "temp" mkdir temp
if not exist "output" mkdir output

echo.
echo ================================================================
echo  [AI Engine] Server dang chay tai:   http://127.0.0.1:8000
echo  [AI Engine] Tai lieu API Swagger:   http://127.0.0.1:8000/docs
echo  [AI Engine] Nhan Ctrl+C de dung server.
echo ================================================================
echo.

python src/server.py
goto END

:NO_PYTHON
echo [LOI] Khong tim thay Python tren he thong [chua cai hoac chua them vao PATH].
echo Vui long cai dat Python 3.10 tro len tai: https://www.python.org/
echo * Luu y: Tich vao muc "Add Python to PATH" khi cai dat.
echo.
pause
exit /b 1

:VENV_FAIL
echo [LOI] Tao moi truong ao .venv that bai.
pause
exit /b 1

:PIP_FAIL
echo [LOI] Cai dat dependencies that bai. Vui long kiem tra ket noi internet.
pause
exit /b 1

:END
=======
cd /d "%~dp0ai-engine"

if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0ai-engine\.venv\Scripts\activate.bat" (
    call "%~dp0ai-engine\.venv\Scripts\activate.bat"
)

echo.
echo [AI Engine] Starting FastAPI server at http://127.0.0.1:8000
echo [AI Engine] Press Ctrl+C to stop
echo.

python src/server.py

>>>>>>> 8ae3a766e952d482da778e3de7378e402743d3dd
pause
