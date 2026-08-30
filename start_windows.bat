@echo off
chcp 65001 >nul
color 0B
echo ==========================================
echo     🎨 LeonardoAPP Windows Launcher 🎨
echo ==========================================
cd /d "%~dp0"

choice /M "Do you want to launch LeonardoAPP?" /C YN
if %ERRORLEVEL% neq 1 (
    echo Launch aborted.
    pause
    exit /b 0
)

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Error: Python 3 is not installed or not in PATH.
    echo Please download it from https://www.python.org/downloads/
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check for Flutter
flutter --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Error: Flutter is not installed or not in PATH.
    echo Please follow instructions at https://docs.flutter.dev/get-started/install/windows
    start https://docs.flutter.dev/get-started/install/windows
    pause
    exit /b 1
)

echo ✅ Python and Flutter found.

:: Setup Virtual Environment
if not exist "venv\" (
    echo ⚙️ Creating Python Virtual Environment...
    python -m venv venv
)

echo 📦 Activating Virtual Environment and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --no-cache-dir

:: Setup .env file
if not exist ".env" (
    echo 🔑 No .env file found. Creating one...
    if exist ".env.example" (
        copy .env.example .env >nul
    ) else (
        echo LLM_API_KEY=> .env
    )
)

:: Check if LLM_API_KEY is empty
findstr /R "^LLM_API_KEY=$" .env >nul
if %ERRORLEVEL% neq 0 goto RunApp

echo ⚠️ Groq API Key is missing in .env.
echo Please get your free key at https://console.groq.com/keys
set /p API_KEY="Enter your Groq API Key: "
findstr /V /R "^LLM_API_KEY=" .env > .env.tmp
echo LLM_API_KEY=%API_KEY%>> .env.tmp
move /Y .env.tmp .env >nul
echo ✅ API Key saved.

:RunApp
:: Run the Flutter App
echo 🚀 Launching LeonardoAPP...
cd frontend || exit /b 1
flutter run -d windows
pause
