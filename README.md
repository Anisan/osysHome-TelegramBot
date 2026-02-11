# TelegramBot - Telegram Bot Integration

![TelegramBot Icon](static/telegrambot.png)

Telegram bot integration for sending messages, receiving commands, and interacting with users via Telegram.

## Description

The `TelegramBot` module provides Telegram bot integration for the osysHome platform. It enables sending notifications, receiving commands, handling messages, and managing Telegram users.

## Main Features

- ✅ **Message Sending**: Send text messages to Telegram users
- ✅ **Command Handling**: Custom command handlers
- ✅ **Message Handling**: Process incoming messages
- ✅ **Callback Handling**: Handle inline keyboard callbacks
- ✅ **User Management**: Manage Telegram users
- ✅ **History**: Message history tracking
- ✅ **Avatar Management**: Download and store user avatars
- ✅ **Event System**: Custom event handling

## Admin Panel

The module provides a comprehensive admin interface:

### Main View
- **Users List**: View all Telegram users
- **Commands**: Manage bot commands
- **Events**: Configure event handlers
- **History**: View message history
- **Settings**: Configure bot token and settings

### User Management
- View Telegram user information
- Edit user settings
- View user avatar
- Track last activity

### Command Configuration
- Create custom commands
- Link commands to object methods
- Configure command responses

## Usage

### Configuring Bot

1. Obtain Telegram bot token from @BotFather
2. Navigate to TelegramBot module
3. Enter bot token in settings
4. Save configuration
5. Bot starts automatically

### Creating Commands

1. Navigate to Commands section
2. Click "Add Command"
3. Enter command name (without /)
4. Link to object method
5. Configure command description
6. Save command

## Technical Details

- **Bot Library**: python-telegram-bot (pyTelegramBotAPI)
- **Polling**: Long polling for message reception
- **Threading**: Separate thread for bot polling
- **Avatar Storage**: Cached avatar images
- **History Cleanup**: Automatic history cleanup

## Version

Current version: **0.2**

## Category

App

## Actions

The module provides the following actions:
- `cycle` - Background bot polling
- `say` - Send messages via Telegram
- `search` - Search Telegram users and commands

## Requirements

- Flask
- pyTelegramBotAPI
- SQLAlchemy
- Requests
- osysHome core system

## Author

osysHome Team

## License

See the main osysHome project license

