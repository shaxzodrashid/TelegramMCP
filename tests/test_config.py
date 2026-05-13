import os
from pathlib import Path
from telegram_mcp.core.config import Settings

def test_config_path_resolution():
    # Create settings with relative paths
    settings = Settings(
        SESSION_NAME="relative_session",
        TELEGRAM_DOWNLOAD_DIR="relative_download",
        TELEGRAM_UPLOAD_DIR="relative_upload"
    )
    
    # Verify they are resolved to absolute paths
    assert os.path.isabs(settings.SESSION_NAME)
    assert os.path.isabs(settings.TELEGRAM_DOWNLOAD_DIR)
    assert os.path.isabs(settings.TELEGRAM_UPLOAD_DIR)
    
    # Verify they contain the expected parts
    assert "relative_session" in settings.SESSION_NAME
    assert "relative_download" in settings.TELEGRAM_DOWNLOAD_DIR
    assert "relative_upload" in settings.TELEGRAM_UPLOAD_DIR
    
    # Verify absolute paths are left as is
    abs_path = str(Path("/tmp/absolute").absolute())
    settings_abs = Settings(SESSION_NAME=abs_path)
    # On Windows, Path("/tmp/absolute").absolute() will include the drive letter
    assert settings_abs.SESSION_NAME == abs_path
