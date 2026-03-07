# Yad2 Car Finder 🚗 
Telegram bot that scrapes [Yad2](https://www.yad2.co.il/vehicles/cars) for car listings based on your filters and sends you notifications when new cars appear

## Features
- **Interactive configuration** - configure manufacturer, model, year range via inline keyboard buttons in Telegram
- **Periodic scanning** - automatically checks for new listings every X minutes (configurable: 5/10/15/30/60) or run a one-time scan
- **Smart notifications** - first scan sends all found listings, subsequent scans only notify about new ones
- **Structured logging** - colored console output with structured JSON kwargs, configurable log level via `LOG_LEVEL` env var
- **Bot commands** - `/start`, `/search`, `/stop`, `/status`

## Setup

### Prerequisites

- Python 3.12+
- Google Chrome installed
- A Telegram bot token (get one from [@BotFather](https://t.me/BotFather))

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create `.env` file and set your Telegram bot token:

```
TELEGRAM_BOT_TOKEN=your-token-here
```

### Running

```bash
python3 src/main.py
```

Then open your bot in Telegram and send `/start`

## Usage

1. `/start` - welcome message with a "New Search" button
2. `/search` - configure a new search (manufacturer, model, year range, scan interval)
3. `/stop` - stop the active scan
4. `/status` - show current scan configuration and how many cars have been found
