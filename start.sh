#!/bin/bash
# Vote Tracker Bot - Start Script
# Aktiviert automatisch das Virtual Environment und startet den Bot

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎮 Vote Tracker Bot - Starting...${NC}"

# Prüfe ob venv existiert
if [ ! -d "venv" ]; then
    echo -e "${BLUE}→ Virtual Environment nicht gefunden. Erstelle...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual Environment erstellt${NC}"
fi

# Aktiviere venv
echo -e "${BLUE}→ Aktiviere Virtual Environment...${NC}"
source venv/bin/activate

# Prüfe ob Dependencies installiert sind
if ! python -c "import aiohttp" 2>/dev/null; then
    echo -e "${BLUE}→ Installiere Dependencies...${NC}"
    pip install -r requirements.txt
fi

# Starte Bot
echo -e "${GREEN}✓ Starte Bot...${NC}\n"
python main.py

# Deaktiviere venv beim Beenden
deactivate
