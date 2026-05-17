import pytest
import os
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch
from telethon import types
from telegram_mcp.models.media import DownloadMediaInput, MediaType
from telegram_mcp.core.file_utils import sanitize_filename, get_safe_path, is_suspicious, validate_size
from telegram_mcp.service.telegram import TelegramService

@pytest.fixture
def telegram_service():
    return TelegramService()

def test_download_media_input_validation():
    # Valid input
    input_data = DownloadMediaInput(chat_id="test_chat", message_id=123)
    assert input_data.chat_id == "test_chat"
    assert input_data.message_id == 123
    assert input_data.allow_suspicious_files is False

    # Negative message_id
    with pytest.raises(ValidationError):
        DownloadMediaInput(chat_id="test_chat", message_id=-1)

    # Extra fields
    with pytest.raises(ValidationError):
        DownloadMediaInput(chat_id="test_chat", message_id=123, extra="extra")

def test_sanitize_filename():
    assert sanitize_filename("test.txt") == "test.txt"
    assert sanitize_filename("test/path.txt") == "path.txt"
    if os.name == "nt":
        assert sanitize_filename(r"test\path.txt") == "path.txt"
    else:
        assert sanitize_filename(r"test\path.txt") == "test_path.txt"
    assert sanitize_filename("../test.txt") == "test.txt"
    assert sanitize_filename("test:*.txt") == "test__.txt"
    assert sanitize_filename("   .hidden") == "hidden"
    assert sanitize_filename("") == "unnamed_file"

def test_is_suspicious():
    assert is_suspicious("safe.jpg")[0] is False
    assert is_suspicious("safe.pdf")[0] is False
    assert is_suspicious("dangerous.exe")[0] is True
    assert is_suspicious("dangerous.EXE")[0] is True
    assert is_suspicious("script.sh")[0] is True
    assert is_suspicious("archive.zip")[0] is True
    # Double extension
    assert is_suspicious("invoice.pdf.exe")[0] is True
    assert is_suspicious("image.jpg.js")[0] is True
    assert is_suspicious("report.tar.gz")[0] is True
    # Bypasses
    assert is_suspicious("malware.exe ")[0] is True
    assert is_suspicious("malware.exe.")[0] is True
    assert is_suspicious("malware.exe . ")[0] is True
    assert is_suspicious(".exe")[0] is True
    assert is_suspicious(".bash")[0] is True

def test_validate_size():
    with patch('telegram_mcp.core.file_utils.settings') as mock_settings:
        mock_settings.TELEGRAM_DOWNLOAD_MAX_FILE_SIZE_MB = 10
        assert validate_size(5 * 1024 * 1024) is True
        assert validate_size(15 * 1024 * 1024) is False

def test_get_safe_path(tmp_path):
    base_dir = str(tmp_path / "storage")
    
    # Simple path
    path = get_safe_path(base_dir, None, "test.txt")
    assert path.name == "test.txt"
    assert str(path).startswith(base_dir)
    
    # Subdirectory
    path = get_safe_path(base_dir, "photos", "test.jpg")
    assert path.name == "test.jpg"
    assert "photos" in str(path)
    
    # Path traversal attempt in sub_dir
    path = get_safe_path(base_dir, "../../etc", "passwd")
    assert "etc" in str(path)
    assert "passwd" in str(path)
    # The utility sanitizes parts to prevent going above base
    # In my implementation: clean_sub = [p for p in clean_sub if p not in ('..', '.', '') and not p.startswith('/')]
    # So "../../etc" becomes ["etc"]
    assert str(path.resolve()).startswith(str(Path(base_dir).resolve()))
    
    # Collision handling
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    Path(base_dir, "test.txt").touch()
    path = get_safe_path(base_dir, None, "test.txt")
    assert path.name == "test_1.txt"

@pytest.mark.asyncio
async def test_detect_media_info(telegram_service):
    # Test Photo
    msg_photo = MagicMock()
    msg_photo.media = MagicMock(spec=types.MessageMediaPhoto)
    msg_photo.media.photo = MagicMock(spec=types.Photo)
    size = MagicMock()
    size.size = 1024
    msg_photo.media.photo.sizes = [size]
    
    info = telegram_service._detect_media_info(msg_photo)
    assert info['type'] == MediaType.photo
    assert info['size_bytes'] == 1024
    assert info['mime_type'] == "image/jpeg"

    # Test Document
    msg_doc = MagicMock()
    msg_doc.media = MagicMock(spec=types.MessageMediaDocument)
    msg_doc.media.document = MagicMock()
    msg_doc.media.document.size = 2048
    msg_doc.media.document.mime_type = "application/pdf"
    filename_attr = types.DocumentAttributeFilename(file_name="report.pdf")
    msg_doc.media.document.attributes = [filename_attr]
    
    info = telegram_service._detect_media_info(msg_doc)
    assert info['type'] == MediaType.document
    assert info['file_name'] == "report.pdf"
    assert info['size_bytes'] == 2048

    # Test Voice
    msg_voice = MagicMock()
    msg_voice.media = MagicMock(spec=types.MessageMediaDocument)
    msg_voice.media.document = MagicMock()
    msg_voice.media.document.size = 500
    msg_voice.media.document.mime_type = "audio/ogg"
    voice_attr = types.DocumentAttributeAudio(duration=10, voice=True)
    msg_voice.media.document.attributes = [voice_attr]
    
    info = telegram_service._detect_media_info(msg_voice)
    assert info['type'] == MediaType.voice

@pytest.mark.asyncio
async def test_download_media_success(telegram_service, tmp_path):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True
    
    # Mock message with photo
    message = MagicMock()
    message.media = MagicMock(spec=types.MessageMediaPhoto)
    message.media.photo = MagicMock(spec=types.Photo)
    size = MagicMock()
    size.size = 100
    message.media.photo.sizes = [size]
    
    telegram_service.client.get_entity.return_value = MagicMock()
    telegram_service.client.get_messages.return_value = message
    
    # Mock download_media to "create" a file
    mock_file = tmp_path / "telegram_123_456.jpg"
    mock_file.touch()
    telegram_service.client.download_media.return_value = str(mock_file)
    
    with patch('telegram_mcp.service.telegram.settings') as mock_settings:
        mock_settings.TELEGRAM_DOWNLOAD_DIR = str(tmp_path)
        mock_settings.TELEGRAM_DOWNLOAD_MAX_FILE_SIZE_MB = 10
        
        result = await telegram_service.download_media(DownloadMediaInput(chat_id=123, message_id=456))
        
        assert result.success is True
        assert result.media_type == MediaType.photo
        assert result.file_name == mock_file.name
        assert result.size_bytes == 0 # file is empty

@pytest.mark.asyncio
async def test_download_media_suspicious_blocked(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True
    
    # Mock message with executable
    message = MagicMock()
    message.media = MagicMock(spec=types.MessageMediaDocument)
    message.media.document = MagicMock()
    message.media.document.size = 100
    message.media.document.mime_type = "application/x-msdownload"
    filename_attr = types.DocumentAttributeFilename(file_name="virus.exe")
    message.media.document.attributes = [filename_attr]
    
    telegram_service.client.get_entity.return_value = MagicMock()
    telegram_service.client.get_messages.return_value = message
    
    result = await telegram_service.download_media(DownloadMediaInput(chat_id=123, message_id=456))
    
    assert result.success is False
    assert result.error_reason == "SUSPICIOUS_FILE_TYPE_BLOCKED"
    assert result.suspicious is True
