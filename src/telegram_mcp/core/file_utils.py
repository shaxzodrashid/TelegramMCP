import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple, List
from .config import settings

# Suspicious extensions as per requirements
SUSPICIOUS_EXTENSIONS = {
    ".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".scr", ".pif",
    ".com", ".dll", ".jar", ".apk", ".ipa", ".deb", ".rpm", ".sh", ".bash", ".zsh", ".fish",
    ".py", ".rb", ".php", ".pl", ".lua", ".reg", ".lnk", ".desktop", ".app", ".dmg", ".iso"
}

ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}

SAFE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}
SAFE_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".aac", ".flac", ".opus"}
SAFE_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
SAFE_DOC_EXTENSIONS = {".pdf", ".txt", ".csv", ".json", ".md", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing unsafe characters and preventing path traversal.
    """
    # Remove path components if any were passed
    filename = os.path.basename(filename)
    
    # Remove control characters
    filename = "".join(ch for ch in filename if unicodedata.category(ch)[0] != "C")
    
    # Replace unsafe characters with underscore
    # Including spaces at the beginning/end and multiple dots
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Final cleanup of leading/trailing whitespace
    filename = filename.strip()
    
    # Prevent hidden files and traversal remnants
    filename = filename.lstrip('.')
    
    # Truncate if too long
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
        
    return filename or "unnamed_file"

def get_safe_path(base_dir: str, sub_dir: str | None, filename: str) -> Path:
    """
    Construct a safe absolute path, preventing path traversal.
    """
    base = Path(base_dir).resolve()
    
    if sub_dir:
        # Sanitize sub_dir to prevent traversal
        # We only allow relative subdirectories within the base
        clean_sub = Path(sub_dir).parts
        # Filter out '..' and empty parts
        clean_sub = [p for p in clean_sub if p not in ('..', '.', '') and not p.startswith('/')]
        target_dir = base.joinpath(*clean_sub)
    else:
        target_dir = base
        
    # Ensure target_dir is still under base
    if not str(target_dir.resolve()).startswith(str(base)):
        target_dir = base
        
    # Create directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = sanitize_filename(filename)
    file_path = target_dir / safe_name
    
    # Handle duplicates by appending suffix
    if file_path.exists():
        name, ext = os.path.splitext(safe_name)
        counter = 1
        while True:
            new_name = f"{name}_{counter}{ext}"
            file_path = target_dir / new_name
            if not file_path.exists():
                break
            counter += 1
            
    return file_path

def is_suspicious(filename: str) -> Tuple[bool, str]:
    """
    Check if a file extension is suspicious.
    Returns (is_suspicious, extension).
    """
    # Check for double extensions
    parts = filename.lower().split('.')
    if len(parts) > 2:
        # e.g. report.pdf.exe -> extension is .exe
        ext = "." + parts[-1]
        if ext in SUSPICIOUS_EXTENSIONS or ext in ARCHIVE_EXTENSIONS:
             return True, ext
        # Check if it has a suspicious extension anywhere except the first part
        # Actually requirements say "treat the last extension as the real extension"
        # and "mark files like report.pdf.exe as suspicious"
        if any(("." + p) in SUSPICIOUS_EXTENSIONS for p in parts[1:]):
            return True, "." + parts[-1]

    ext = Path(filename).suffix.lower()
    if ext in SUSPICIOUS_EXTENSIONS:
        return True, ext
    if ext in ARCHIVE_EXTENSIONS:
        return True, ext
        
    return False, ext

def validate_size(size_bytes: int) -> bool:
    """
    Validate if the file size is within download limits.
    """
    max_bytes = settings.TELEGRAM_DOWNLOAD_MAX_FILE_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes

def validate_upload_size(size_bytes: int) -> bool:
    """
    Validate if the file size is within upload limits.
    """
    max_bytes = settings.TELEGRAM_UPLOAD_MAX_FILE_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes

def validate_safe_upload_path(file_path: str) -> Path | None:
    """
    Validate that the file path is safe to upload (not path traversing outside allowed directories).
    Returns the resolved Path if safe, or None if unsafe.
    """
    path = Path(file_path).resolve()
    
    # Allowed directories
    allowed_dirs = [
        Path(settings.TELEGRAM_UPLOAD_DIR).resolve(),
        Path(settings.TELEGRAM_DOWNLOAD_DIR).resolve()
    ]
    
    # Ensure allowed dirs exist
    for allowed_dir in allowed_dirs:
        allowed_dir.mkdir(parents=True, exist_ok=True)
        if str(path).startswith(str(allowed_dir)):
            return path
            
    return None

