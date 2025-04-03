# Easy Match Win - Betting Signal Bot

A Telegram bot integrated with a Flask health check server for submitting betting signals.

## Overview

This project consists of:
1. A Telegram bot that collects betting signal information from users and posts it to a specified channel
2. A simple Flask server providing a health check endpoint

## Features

- Telegram Bot:
  - Step-by-step input collection for match details
  - Input validation for date, odds, and score
  - Image upload support
  - Edit functionality for submitted data
  - Posting to a Telegram channel
- Flask Server:
  - Basic health check endpoint returning status 200
- Concurrent running of both services
- Graceful shutdown with Ctrl+C

## Prerequisites

- Python 3.8+
- Telegram Bot Token (configured in code)
- Telegram Channel ID (configured in code)

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd <repository-directory>
```

2. Create a virtual environment (optional but recommended):
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

## Usage

1. Configure the bot:
- Replace `TOKEN` in the code with your Telegram Bot token
- Replace `CHANNEL_ID` with your Telegram channel ID

2. Run the application:
```
python betting_bot_with_flask.py
```

3. Access the services:
- Telegram Bot: Interact via Telegram using commands (/start, /betting_signal, /cancel)
- Flask Server: Visit `http://localhost:5000/` for health check

4. Stop the application:
- Press Ctrl+C to gracefully shut down both the bot and server

## Commands

- `/start`: Displays welcome message
- `/betting_signal`: Starts the betting signal submission process
- `/cancel`: Cancels the current submission process

## Project Structure

- `betting_bot_with_flask.py`: Main application code
- `requirements.txt`: Project dependencies
- `README.md`: This file

## Dependencies

- python-telegram-bot==20.7
- flask==3.0.3

## Notes

- The Flask server runs on port 5000 by default
- Both services run concurrently using threading
- Logging is configured to provide info-level messages
- The bot stores user data temporarily in memory

## Contributing

Feel free to submit issues or pull requests to improve the project.
