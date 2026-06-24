import asyncio
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from telethon import TelegramClient
from .core.config import settings
from .core.logger import logger

from .service.telegram import telegram_service

app = typer.Typer(
    help="Telegram MCP CLI - Configuration and Management",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def update_env_file(key: str, value: str):
    # Sanitize value to prevent environment variable injection
    value = str(value).translate(str.maketrans("", "", "\n\r"))

    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = 0o600
    with open(os.open(env_path, flags, mode), "w") as f:
        f.writelines(new_lines)

    # Enforce 0600 in case the file already existed with wider permissions
    try:
        os.chmod(env_path, 0o600)
    except OSError as e:
        logger.warning("Could not secure env file permissions: {}", e)


async def auth_flow():
    console.print(Panel.fit("Telegram Authentication", style="bold blue"))

    api_id = settings.API_ID
    api_hash = settings.API_HASH

    if not api_id or api_id == 0 or not api_hash or api_hash == "placeholder":
        console.print("[yellow]Telegram API credentials are missing.[/yellow]")
        console.print(
            "You can get them from [link=https://my.telegram.org/apps]https://my.telegram.org/apps[/link]"
        )

        api_id_input = Prompt.ask("Enter your API_ID")
        api_hash_input = Prompt.ask("Enter your API_HASH", password=True)

        update_env_file("API_ID", api_id_input)
        update_env_file("API_HASH", api_hash_input)

        # Update settings for current process
        settings.API_ID = int(api_id_input)
        settings.API_HASH = api_hash_input
        api_id = settings.API_ID
        api_hash = settings.API_HASH

    # Pre-create session file securely to prevent TOCTOU vulnerability
    session_file = f"{settings.SESSION_NAME}.session"
    if not os.path.exists(session_file):
        try:
            fd = os.open(session_file, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)
        except OSError as e:
            logger.warning("Could not pre-create session file: {}", e)

    client = TelegramClient(settings.SESSION_NAME, api_id, api_hash)

    console.print("\n[bold green]Connecting to Telegram...[/bold green]")
    await client.connect()

    # Enforce secure permissions on the session file
    if os.path.exists(session_file):
        try:
            os.chmod(session_file, 0o600)
        except OSError as e:
            logger.warning("Could not secure session file permissions: {}", e)

    if not await client.is_user_authorized():
        phone = Prompt.ask(
            "Enter your phone number (with country code, e.g., +1234567890)"
        )
        try:
            await client.send_code_request(phone)
        except Exception as e:
            console.print("[bold red]Failed to send code:[/bold red]", str(e))
            return

        code = Prompt.ask("Enter the code you received", password=True)
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            # Handle 2FA if needed
            from telethon.errors import SessionPasswordNeededError

            if isinstance(e, SessionPasswordNeededError):
                password = Prompt.ask(
                    "Two-step verification is enabled. Enter your password",
                    password=True,
                )
                try:
                    await client.sign_in(password=password)
                except Exception as e2:
                    console.print(
                        "[bold red]Password verification failed:[/bold red]", str(e2)
                    )
                    return
            else:
                console.print("[bold red]Authentication failed:[/bold red]", str(e))
                return

    me = await client.get_me()
    console.print(
        f"\n[bold green]Successfully authenticated as {me.first_name} (@{me.username or 'N/A'}) [ID: {me.id}][/bold green]"
    )
    await client.disconnect()


@app.command()
def auth():
    """
    Authenticate with Telegram interactively.
    """
    asyncio.run(auth_flow())


@app.command()
def status():
    """
    Check the current authentication status.
    """

    async def check_status():
        try:
            me = await telegram_service.get_me()
            if me:
                console.print(
                    Panel(
                        f"[bold green]Authenticated[/bold green]\n"
                        f"User: {me.first_name} (@{me.username or 'N/A'})\n"
                        f"ID: {me.id}",
                        title="Telegram Status",
                    )
                )
            else:
                console.print(
                    Panel(
                        "[bold red]Not authenticated[/bold red]\n"
                        "Run 'telegram-mcp auth' to log in.",
                        title="Telegram Status",
                    )
                )
        except Exception as e:
            console.print("[bold red]Error checking status:[/bold red]", str(e))
        finally:
            await telegram_service.stop()

    asyncio.run(check_status())


@app.command()
def config():
    """
    Show current configuration.
    """
    api_hash_display = (
        "********" if settings.API_HASH != "placeholder" else "[red]Not set[/red]"
    )
    api_id_display = (
        str(settings.API_ID) if settings.API_ID != 0 else "[red]Not set[/red]"
    )

    console.print(
        Panel(
            f"[bold blue]Telegram Credentials[/bold blue]\n"
            f"API_ID: {api_id_display}\n"
            f"API_HASH: {api_hash_display}\n"
            f"SESSION_NAME: {settings.SESSION_NAME}\n\n"
            f"[bold blue]Server Settings[/bold blue]\n"
            f"SERVER_NAME: {settings.SERVER_NAME}\n"
            f"VERSION: {settings.SERVER_VERSION}\n"
            f"DEBUG: {settings.DEBUG}",
            title="Current Configuration",
        )
    )


async def _logout_flow():
    session_file = f"{settings.SESSION_NAME}.session"
    if not os.path.exists(session_file):
        console.print("[yellow]No active session found.[/yellow]")
        return

    # Attempt to securely log out from the server
    client = None
    logged_out_securely = False
    try:
        if settings.API_ID != 0 and settings.API_HASH != "placeholder":
            client = TelegramClient(settings.SESSION_NAME, settings.API_ID, settings.API_HASH)
            await client.connect()
            # If connected and authorized, log out to revoke the token on Telegram's side
            if await client.is_user_authorized():
                await client.log_out()
                logged_out_securely = True
                console.print("[bold green]Successfully logged out from Telegram server.[/bold green]")
    except Exception as e:
        logger.warning("Could not revoke server-side session, falling back to local deletion: {}", e)
    finally:
        if client:
            await client.disconnect()

    # Fallback/cleanup: manually delete the local session file if log_out didn't already remove it
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
            console.print("[bold green]Local session file deleted.[/bold green]")
        except OSError as e:
            console.print(f"[bold red]Failed to delete session file locally: {e}[/bold red]")
    elif not logged_out_securely:
        console.print("[bold green]Session file no longer exists.[/bold green]")


@app.command()
def logout():
    """
    Log out from Telegram and delete the session file securely from the server.
    """
    async def logout_flow():
        if not typer.confirm(
            "Are you sure you want to log out and delete the session file?"
        ):
            return

        session_file = f"{settings.SESSION_NAME}.session"
        client = TelegramClient(settings.SESSION_NAME, settings.API_ID, settings.API_HASH)

    async def secure_logout():
        session_file = f"{settings.SESSION_NAME}.session"
        if not os.path.exists(session_file):
            console.print("[yellow]No active session found.[/yellow]")
            return

        api_id = settings.API_ID
        api_hash = settings.API_HASH

        if not api_id or api_id == 0 or not api_hash or api_hash == "placeholder":
            # Can't connect without credentials, fallback to simple file deletion
            try:
                os.remove(session_file)
                console.print("[bold green]Local session file deleted (missing credentials for server logout).[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Failed to delete local session file:[/bold red] {e}")
            return

        client = TelegramClient(settings.SESSION_NAME, api_id, api_hash)

        console.print("[bold blue]Connecting to Telegram to revoke session...[/bold blue]")
        try:
            await client.connect()
            if await client.is_user_authorized():
                await client.log_out()
                console.print(
                    "[bold green]Successfully logged out and session token revoked.[/bold green]"
                )
            else:
                console.print("[yellow]No active server-side session found.[/yellow]")
        except Exception as e:
            console.print("[bold red]Failed to communicate with Telegram server:[/bold red]", str(e))
        finally:
            await client.disconnect()

        # Fallback to local deletion
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                console.print(
                    "[bold green]Local session file deleted.[/bold green]"
                )
            except Exception as e:
                console.print("[bold red]Failed to delete session file:[/bold red]", str(e))

    asyncio.run(logout_flow())



@app.command()
def server():
    """
    Run the MCP server.
    """
    import sys
    from .server import mcp

    # IMPORTANT: Use stderr for messages to avoid breaking MCP stdio transport handshake
    console.print(
        "[bold green]Starting Telegram MCP Server...[/bold green]", file=sys.stderr
    )
    # mcp.run() will start the stdio transport
    mcp.run()


if __name__ == "__main__":
    app()
