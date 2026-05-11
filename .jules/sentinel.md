## 2024-05-08 - Insecure File Permissions for Telethon Sessions and Credentials
**Vulnerability:** The Telegram MCP server was creating `.env` (containing API credentials) and `.session` (containing Telegram authentication tokens) files with default umask permissions, making them world-readable (0644).
**Learning:** Default file creation on Linux/Unix systems uses the process's umask, which typically results in 0644 for files. When a library like Telethon creates a session file (SQLite database containing tokens), it does not automatically restrict file permissions. Similarly, manually writing a config file containing secrets requires explicitly restricting file permissions. This is a critical risk for CLI tools and servers that store credentials on disk.
**Prevention:** Always use `os.open` with specific secure modes (e.g., `0o600`) when creating files that will hold sensitive data. For third-party libraries that create files, explicitly `os.chmod` the files to `0600` after initialization to lock them down.
## 2024-05-09 - Information Leakage in Logs and Error Messages
**Vulnerability:** The Telegram MCP server was dumping sensitive debug logs to a world-readable `logs/` directory. Furthermore, endpoints like `get_account_info` and `list_chats` were directly returning the raw exception `str(e)` on error, which could leak stack traces or internal state to clients.
**Learning:** Returning `str(e)` in an API or CLI response often breaks the "Fail securely" principle by exposing more details than the user needs. Also, local log directories must have restricted permissions (e.g. `0o700`) to prevent local unprivileged users from reading potentially sensitive data, especially when using Telethon, which can generate verbose network logs.
**Prevention:** Catch generic exceptions and return safe, generalized error strings (e.g. "An unexpected error occurred"). Use `os.makedirs(mode=0o700)` for local log directories and set the default file log level to `INFO` rather than `DEBUG`.
## 2026-05-11 - [TOCTOU Vulnerability in Session File Creation]
**Vulnerability:** Telethon  files (which contain sensitive cryptographic keys) were briefly created with default (potentially world-readable) OS permissions before being secured via .
**Learning:** A Time-of-Check to Time-of-Use (TOCTOU) race condition allowed a brief window where the session file could be read by unauthorized users on the system.
**Prevention:** Pre-create sensitive files using  with strict permissions (e.g.,  and ) *before* allowing libraries to access or write to them.
## 2025-05-11 - [TOCTOU Vulnerability in Session File Creation]
**Vulnerability:** Telethon `.session` files (which contain sensitive cryptographic keys) were briefly created with default (potentially world-readable) OS permissions before being secured via `os.chmod`.
**Learning:** A Time-of-Check to Time-of-Use (TOCTOU) race condition allowed a brief window where the session file could be read by unauthorized users on the system.
**Prevention:** Pre-create sensitive files using `os.open` with strict permissions (e.g., `0o600` and `O_CREAT | O_WRONLY`) *before* allowing libraries to access or write to them.
