# Telegram MCP Server

A Model Context Protocol (MCP) server for Telegram, built with Telethon and FastMCP.

## Features
- **MTProto Support**: High-performance communication via Telethon.
- **FastMCP**: Seamless integration with AI agents.
- **Async & Performance**: Optimized for speed and concurrency.
- **Professional Core**: Built-in logging and configuration.

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

Run the MCP server:
```bash
uv run python -m telegram_mcp.server
```

## Structure
- `src/telegram_mcp/core/`: Essential utilities (logger, config).
- `src/telegram_mcp/service/`: Business logic and external API clients.
- `src/telegram_mcp/models/`: Pydantic data models.
- `src/telegram_mcp/server.py`: MCP server definition and tool registration.
