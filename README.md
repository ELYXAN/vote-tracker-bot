# 🎮 Vote Tracker Bot

A high-performance Twitch bot for managing Channel Point votes with **SQLite database** and automatic Google Sheets synchronization.

## ✨ Features

### 🚀 Performance & Speed
- **SQLite Database**: Lightning-fast vote processing (no API rate limits!)
- **Optimized Vote Detection**: Parallel reward checking and 1-second polling interval
- **Instant Vote Fulfillment**: Votes are marked as fulfilled immediately after processing
- **Async Sync Worker**: Automatic background synchronization to Google Sheets every 5 seconds
- **Vote History**: Complete history of all votes with timestamps and user information

### 🎯 Core Features
- **Automatic Vote Processing**: Twitch Channel Point Redemptions (Normal, Super, Ultra Votes)
- **Manual Vote Input**: CLI interface for manual vote entry during runtime
- **Fuzzy Matching**: Intelligent game name recognition with configurable match score
- **Automatic Ranking**: Extremely fast ranking calculation using database queries
- **Chat Integration**: Automatic notifications in Twitch chat
- **Token Management**: Automatic OAuth2 token refresh
- **Modular Architecture**: Clean code structure for easy maintenance

### 🎨 User Experience
- **Colorful Terminal Output**: Beautiful colored messages for better readability
  - 🟢 Green for success messages
  - 🔴 Red for errors
  - 🟡 Yellow for warnings
  - 🔵 Blue for prompts
  - 🟣 Magenta for highlights
  - 🔷 Cyan for info messages
- **Silent Background Sync**: Sync worker runs quietly without interrupting manual input
- **Real-time Updates**: Instant feedback on vote processing

### 📊 Statistics & Analytics
- **Vote History**: Every vote is logged (user, time, type, weight)
- **Statistics**: Total votes, unique voters, vote counts per game
- **Google Sheets as View**: Viewers can still see the spreadsheet (auto-sync)

## 📦 Project Structure

```
vote-tracker-bot/
├── main.py                           # Main entry point
├── config.json                       # Bot configuration
├── secrets.json                      # Sensitive credentials (DO NOT COMMIT!)
├── Vote tracking.json                # Google Service Account credentials
├── votes.db                          # SQLite database (auto-created)
├── requirements.txt                  # Python dependencies
├── start.sh                          # Convenient startup script
├── create_rewards.py                 # Helper script to create Channel Point rewards
├── get_reward_ids.py                 # Helper script to list existing rewards
├── README.md                         # This file
│
└── src/                              # Source code
    ├── config/                       # Configuration management
    │   ├── constants.py              # Constants and defaults
    │   └── loader.py                 # Config/Secrets loading/saving
    │
    ├── auth/                         # Authentication
    │   ├── __init__.py               # Module exports
    │   ├── token_manager.py          # Token validation and refresh
    │   └── oauth_flow.py             # OAuth2 authorization flow
    │
    ├── database/                     # ⚡ Database layer
    │   ├── models.py                 # DB schema and initialization
    │   ├── operations.py             # CRUD operations
    │   └── sync_worker.py            # Async Sheets sync worker
    │
    ├── twitch/                       # Twitch API integration
    │   ├── redemptions.py            # Channel Points listener
    │   └── chat.py                   # Chat messages
    │
    ├── sheets/                       # Google Sheets integration
    │   ├── manager.py                # Initialization and migration
    │   └── operations.py             # Legacy sorting (for fallback)
    │
    ├── voting/                       # Vote processing
    │   ├── processor.py              # Main vote logic (DB-optimized)
    │   ├── ranking.py                # Ranking calculation (DB queries)
    │   └── manual_input.py           # Manual CLI input
    │
    └── utils/                        # Utility functions
        ├── banner.py                 # ASCII banner
        ├── colors.py                 # Terminal color utilities
        └── storage.py                # Vote ID persistence
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Twitch Developer Account
- Google Cloud Account (for Sheets API)

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd vote-tracker-bot-main
```

### 2. Install Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create Twitch Application

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create a new Application
3. Set OAuth Redirect URL to: `http://localhost`
4. Note your Client ID and Client Secret

**Required OAuth Scopes:**
- **Streamer Account**: `channel:read:redemptions channel:manage:redemptions`
- **Chat Bot Account**: `chat:read chat:edit user:write:chat`

### 4. Create Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Sheets API
4. Create a Service Account
5. Download the JSON credentials
6. Rename the file to `Vote tracking.json`
7. Share your Google Sheet with the Service Account email (found in the JSON)

### 5. Configuration

#### Create `secrets.json`
```json
{
    "streamer": {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET"
    },
    "chat_bot": {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET"
    },
    "broadcaster_id": "YOUR_BROADCASTER_ID"
}
```

**Note**: `access_token`, `refresh_token`, and `token_expiry` will be automatically filled during the OAuth flow.

#### Configure `config.json`
```json
{
    "twitch_username": "your_username",
    "rewards": {
        "normal_vote": "REWARD_ID_HERE",
        "super_vote": "REWARD_ID_HERE",
        "ultra_vote": "REWARD_ID_HERE"
    },
    "spreadsheet_id": "YOUR_SPREADSHEET_ID",
    "min_match_score": 80,
    "normal_vote_weight": 1,
    "super_vote_weight": 10,
    "ultra_vote_weight": 25,
    "database": {
        "enabled": true,
        "sync_interval": 5
    }
}
```

### 6. Create Channel Point Rewards

**Important**: Rewards must be created with the same Client ID used in `secrets.json` to avoid authorization issues.

#### Option A: Use the Helper Script (Recommended)
```bash
python3 create_rewards.py
```

This script will:
- Check for existing rewards
- Optionally delete old rewards
- Create new rewards with the correct Client ID
- Automatically update `config.json` with the new reward IDs

#### Option B: List Existing Rewards
```bash
python3 get_reward_ids.py
```

This will show all your Channel Point rewards with their IDs.

## 🎯 Usage

### Start the Bot

#### Using the Startup Script (Recommended)

**Linux/macOS:**
```bash
./start.sh
```

**Windows 10:**
```batch
start.bat
```

#### Manual Start
```bash
# Linux/macOS
python3 main.py

# Windows
python main.py
```

### First-Time Authorization

On first run, the bot will:
1. Open your browser automatically
2. Request authorization for both accounts (Streamer + Chat Bot)
3. You'll be redirected to `http://localhost?code=...`
4. Copy the `code` parameter from the URL
5. Paste it into the terminal when prompted
6. Tokens will be automatically saved

### Manual Vote Input

While the bot is running, you can manually add votes:
1. Enter a game name (or type `exit` to quit)
2. Enter the number of votes
3. The bot processes the vote immediately

The bot uses fuzzy matching to find similar game names automatically.

## 📊 Google Spreadsheet Format

Your spreadsheet should have this format:

| Votes | Game |
|-------|------|
| 42    | Elden Ring |
| 35    | Dark Souls 3 |
| 28    | Sekiro |

- Column A: Votes (numbers)
- Column B: Game (game names)
- Header in row 1

The bot automatically syncs the database to this format every 5 seconds (configurable).

## ⚙️ Configuration Options

### Vote Weights
- `normal_vote_weight`: Default 1 point
- `super_vote_weight`: Default 10 points
- `ultra_vote_weight`: Default 25 points

### Fuzzy Matching
- `min_match_score`: Minimum score for fuzzy match (0-100, default: 80)

### Database & Sync
- `database.enabled`: Enable/disable database (default: true)
- `database.sync_interval`: Sync interval in seconds (default: 5)

### Cache
- Game list cache validity: 5 minutes (300 seconds)
- Cache is automatically updated when new games are added

## 🛠️ Development

### Code Style
- Python 3.8+
- Async/Await for all I/O operations
- Type hints recommended
- Docstrings for all public functions

### Extending Modules
New features should be added to appropriate modules:
- Twitch features → `src/twitch/`
- Google Sheets features → `src/sheets/`
- Vote logic → `src/voting/`
- Utilities → `src/utils/`

## 📝 Logs and Debugging

The bot provides detailed colored output:
- 🟢 **Green**: Successful operations
- 🔴 **Red**: Errors
- 🟡 **Yellow**: Warnings
- 🔵 **Blue**: Prompts and input requests
- 🔷 **Cyan**: Informational messages
- 🟣 **Magenta**: Important highlights (vote counts, game names)

Unprocessed games are saved to `inacurate_games.csv` for review.

## 🔒 Security

**IMPORTANT**: 
- **NEVER commit** `secrets.json`!
- **NEVER commit** `Vote tracking.json`!
- Add both to `.gitignore`
- Keep your Client Secrets secure

## 🚀 Performance Optimizations

This version includes several performance improvements:

- **5x Faster Vote Detection**: Reduced polling interval from 5s to 1s
- **Parallel Reward Checking**: All reward types checked simultaneously
- **Instant Vote Fulfillment**: Votes marked as fulfilled immediately
- **Parallel Operations**: Fulfill vote and send chat message simultaneously
- **Cached Bot User ID**: Eliminates repeated API calls
- **Non-blocking Chat Messages**: Chat messages don't block vote processing

## 📋 Requirements

See `requirements.txt` for full list. Main dependencies:
- `aiohttp` - Async HTTP client
- `aiosqlite` - Async SQLite database
- `gspread` - Google Sheets API
- `fuzzywuzzy` - Fuzzy string matching
- `pandas` - Data manipulation

## 👤 Author

**ELYXAN / KUS_SWAT_**
- Twitch: [kus_swat__](https://twitch.tv/kus_swat__)
- Version: 3.1 - Performance Optimized

## 📄 License

This project is for personal use.

## 🙏 Acknowledgments

Built with ❤️ for the Twitch streaming community.
