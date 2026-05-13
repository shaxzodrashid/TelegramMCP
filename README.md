# Telegram MCP Server

A Model Context Protocol (MCP) server for Telegram, built with Telethon and FastMCP.

## Features
- **MTProto Support**: High-performance communication via Telethon.
- **FastMCP**: Seamless integration with AI agents.
- **Async & Performance**: Optimized for speed and concurrency.
- **Professional Core**: Built-in logging, caching, and configuration.

## Setup

1. Install `uv` if you haven't already.
2. Clone the repository.
3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Fill in your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).
5. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Authentication
Before running the server, you need to authenticate with Telegram:
```bash
uv run telegram-mcp auth
```

### Run Server
```bash
uv run telegram-mcp server
```
Or run directly via the module:
```bash
uv run python -m telegram_mcp.server
```

## Codex Integration

This server is fully compatible with [Codex](https://codex.openai.com/). 

### Local Plugin Discovery
The repository includes a `.codex-plugin/` directory for native discovery. You can add this directory as a local plugin in your Codex settings.

### Manual Configuration
Add the following to your `~/.codex/config.toml` (replace with your absolute paths):

```toml
[mcp_servers.telegrammcp]
command = "/absolute/path/to/TelegramMCP/.venv/bin/python"
args = ["-m", "telegram_mcp.server"]
cwd = "/absolute/path/to/TelegramMCP"
startup_timeout_sec = 30
tool_timeout_sec = 120
env_vars = ["API_ID", "API_HASH", "SESSION_NAME", "TELEGRAM_PHONE_NUMBER"]

[mcp_servers.telegrammcp.env]
SERVER_NAME = "telegrammcp"
LOG_LEVEL = "INFO"
TELEGRAM_DOWNLOAD_DIR = "/absolute/path/to/TelegramMCP/storage/downloads/telegram"
TELEGRAM_UPLOAD_DIR = "/absolute/path/to/TelegramMCP/storage/uploads/telegram"
```

## Tools

### Account Info
- `get_account_info`: Returns information about the currently logged-in Telegram account.

### Chat Management
- `list_chats`: List Telegram chats/dialogs with search and filtering.

### Media Download
- `download_telegram_media`: Safely download media attachments from a Telegram message.
  - **Inputs**: `chat_id`, `message_id`, `download_directory` (optional), `preferred_file_name` (optional), `allow_suspicious_files` (default: false).
  - **Safety Features**: 
    - Prevents path traversal.
    - Blocks suspicious file types (executables, archives) by default.
    - Sanitizes filenames.
    - Limits file size (default 100MB).
    - Ensures downloads stay within a designated storage directory.

### Sending Messages
- `telegram_send_message`: Safely send a message or media file to a Telegram chat, or reply to an existing message.
  - **Inputs**: `chat` (required), `message` (optional), `reply_to_message_id` (optional), `media` (optional), `parse_mode` (optional), `silent` (optional), `disable_link_preview` (optional).
  - **Safety Features**:
    - Strictly blocks dangerous file extensions (`.exe`, `.sh`, `.bat`, etc.) for uploads.
    - Prevents path traversal for local media files.
    - Enforces max upload file size (default 100MB).
    - Forbids URL-based media fetching for security.
  - **Examples**:
    - **Send text**: `{"chat": "@username", "message": "Hello"}`
    - **Reply with text**: `{"chat": "123456", "message": "Got it!", "reply_to_message_id": 987}`
    - **Send photo**: `{"chat": "@username", "media": {"path": "C:/safe/dir/photo.jpg", "type": "photo"}}`

## Structure
- `src/telegram_mcp/core/`: Essential utilities (logger, cache, config).
- `src/telegram_mcp/service/`: Business logic and external API clients.
- `src/telegram_mcp/models/`: Pydantic data models.
- `src/telegram_mcp/server.py`: MCP server definition and tool registration.
