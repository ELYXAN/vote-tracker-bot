# 🚀 Setup & Quick Start

## Virtual Environment Setup

Das Virtual Environment ist bereits eingerichtet! Alle Python-Dependencies sind installiert.

## Option 1: Start-Script nutzen (Empfohlen)

Einfach das Start-Script ausführen:

```bash
./start.sh
```

Das Script:
- ✓ Aktiviert automatisch das Virtual Environment
- ✓ Prüft ob alle Dependencies installiert sind
- ✓ Startet den Bot
- ✓ Deaktiviert das venv beim Beenden

## Option 2: Manuell starten

Wenn du das venv manuell aktivieren möchtest:

### Linux/Mac:
```bash
# Aktivieren
source venv/bin/activate

# Bot starten
python main.py

# Deaktivieren (nach dem Beenden)
deactivate
```

### Windows:
```bash
# Aktivieren
venv\Scripts\activate

# Bot starten
python main.py

# Deaktivieren (nach dem Beenden)
deactivate
```

## Dependencies nachinstallieren/aktualisieren

Falls du später Dependencies aktualisieren möchtest:

```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Installierte Packages

- ✓ aiohttp (Async HTTP Client)
- ✓ aiosqlite (Async SQLite)
- ✓ gspread (Google Sheets API)
- ✓ oauth2client (Google Auth)
- ✓ pandas (Data Processing)
- ✓ fuzzywuzzy + python-Levenshtein (Fuzzy Matching)

## Troubleshooting

### "ModuleNotFoundError"
→ Stelle sicher, dass das venv aktiviert ist:
```bash
source venv/bin/activate
```

### Dependencies neu installieren
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Permissions-Fehler bei start.sh
```bash
chmod +x start.sh
```

## Erste Schritte nach Installation

1. **secrets.json** ausfüllen (Client IDs, Secrets, Broadcaster ID)
2. **config.json** prüfen (Reward IDs, Spreadsheet ID)
3. **Vote tracking.json** hinzufügen (Google Service Account)
4. Bot starten: `./start.sh`

Bei Fragen siehe README.md für detaillierte Dokumentation!
