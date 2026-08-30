#!/usr/bin/env bash

# Change to the directory of this script
cd "$(dirname "$0")"

echo "=========================================="
echo "    🎨 LeonardoAPP Mac Launcher 🎨        "
echo "=========================================="

echo -n "Do you want to launch LeonardoAPP? (y/n): "
read -n 1 -r CONFIRM
echo ""
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Launch aborted."
    exit 0
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH."
    echo "Please download it from https://www.python.org/downloads/mac-osx/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check for Flutter
if ! command -v flutter &> /dev/null; then
    echo "❌ Error: Flutter is not installed or not in PATH."
    echo "Please follow instructions at https://docs.flutter.dev/get-started/install/macos"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

echo "✅ Python and Flutter found."

# Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "⚙️ Creating Python Virtual Environment..."
    python3 -m venv venv
fi

echo "📦 Activating Virtual Environment and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir

# Setup .env file
if [ ! -f ".env" ]; then
    echo "🔑 No .env file found. Creating one..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo "LLM_API_KEY=" > .env
    fi
fi

if grep -qE '^LLM_API_KEY=$|^LLM_API_KEY=\s*$' .env; then
    echo "⚠️ Groq API Key is missing in .env."
    echo "Please enter your Groq API Key (get it from https://console.groq.com/keys):"
    read -r API_KEY
    sed -i '' "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" .env
    echo "✅ API Key saved."
fi

# Run the Flutter App
echo "🚀 Launching LeonardoAPP..."
cd frontend || { echo "❌ Error: frontend directory not found"; exit 1; }
flutter run -d macos
