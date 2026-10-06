@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating local virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "C:\Users\madda\.gemini\antigravity\scratch\secureshare\.venv\Scripts\activate.bat" (
    echo [*] Activating SecureShare virtual environment...
    call "C:\Users\madda\.gemini\antigravity\scratch\secureshare\.venv\Scripts\activate.bat"
) else (
    echo [!] Virtual environment not found. Running with system python...
)
echo [*] Starting SecureShare server...
python run.py
pause
