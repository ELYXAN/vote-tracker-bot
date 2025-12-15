@echo off
REM Vote Tracker Bot - Start Script for Windows
REM Automatically activates virtual environment and starts the bot

echo 🎮 Vote Tracker Bot - Starting...

REM Check if venv exists
if not exist "venv" (
    echo → Virtual Environment not found. Creating...
    python -m venv venv
    echo ✓ Virtual Environment created
)

REM Activate venv
echo → Activating Virtual Environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import aiohttp" 2>nul
if errorlevel 1 (
    echo → Installing dependencies...
    pip install -r requirements.txt
)

REM Start bot
echo ✓ Starting bot...
echo.
python main.py

REM Deactivate venv when done
deactivate

