from __future__ import annotations

import os
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime


def ensure_directory(directory: Path) -> Path:
    """Ensure directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    return file_path.stat().st_size if file_path.exists() else 0


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    return get_file_size(file_path) / (1024 * 1024)


def safe_delete_file(file_path: Path) -> bool:
    """Safely delete a file with error handling."""
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception:
        return False


def safe_copy_file(src: Path, dst: Path) -> bool:
    """Safely copy a file with error handling."""
    try:
        ensure_directory(dst.parent)
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False


def safe_move_file(src: Path, dst: Path) -> bool:
    """Safely move a file with error handling."""
    try:
        ensure_directory(dst.parent)
        shutil.move(str(src), str(dst))
        return True
    except Exception:
        return False


def list_files_by_extension(directory: Path, extension: str) -> List[Path]:
    """List all files with a specific extension in a directory."""
    if not directory.exists():
        return []
    
    return list(directory.glob(f"*.{extension.lstrip('.')}"))


def list_files_by_pattern(directory: Path, pattern: str) -> List[Path]:
    """List all files matching a pattern in a directory."""
    if not directory.exists():
        return []
    
    return list(directory.glob(pattern))


def get_directory_size(directory: Path) -> int:
    """Get total size of a directory in bytes."""
    total_size = 0
    if directory.exists():
        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
    return total_size


def get_directory_size_mb(directory: Path) -> float:
    """Get total size of a directory in megabytes."""
    return get_directory_size(directory) / (1024 * 1024)


def count_files(directory: Path) -> int:
    """Count total files in a directory recursively."""
    if not directory.exists():
        return 0
    
    return len(list(directory.rglob("*")))


def is_image_file(file_path: Path) -> bool:
    """Check if file is an image based on extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    return file_path.suffix.lower() in image_extensions


def is_valid_filename(filename: str) -> bool:
    """Check if filename is valid."""
    if not filename:
        return False
    
    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        if char in filename:
            return False
    
    # Check for reserved names (Windows)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
    if filename.upper().split('.')[0] in reserved_names:
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    if not filename:
        return "unnamed"
    
    # Remove invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Ensure it's not empty
    if not filename:
        filename = "unnamed"
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def create_backup_file(file_path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """Create a backup of a file."""
    if not file_path.exists():
        return None
    
    if backup_dir is None:
        backup_dir = file_path.parent / "backups"
    
    ensure_directory(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_filename
    
    if safe_copy_file(file_path, backup_path):
        return backup_path
    
    return None


def cleanup_old_files(directory: Path, days: int = 30) -> int:
    """Clean up files older than specified days."""
    if not directory.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            if file_path.stat().st_mtime < cutoff_time:
                if safe_delete_file(file_path):
                    deleted_count += 1
    
    return deleted_count


def get_file_creation_time(file_path: Path) -> Optional[datetime]:
    """Get file creation time."""
    if not file_path.exists():
        return None
    
    return datetime.fromtimestamp(file_path.stat().st_ctime)


def get_file_modification_time(file_path: Path) -> Optional[datetime]:
    """Get file modification time."""
    if not file_path.exists():
        return None
    
    return datetime.fromtimestamp(file_path.stat().st_mtime)


def is_file_recent(file_path: Path, hours: int = 24) -> bool:
    """Check if file was modified within specified hours."""
    mod_time = get_file_modification_time(file_path)
    if not mod_time:
        return False
    
    time_diff = (datetime.now() - mod_time).total_seconds()
    return time_diff < (hours * 3600)


def read_file_safe(file_path: Path, default: str = "") -> str:
    """Safely read file content with error handling."""
    try:
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return default
    except Exception:
        return default


def write_file_safe(file_path: Path, content: str) -> bool:
    """Safely write file content with error handling."""
    try:
        ensure_directory(file_path.parent)
        file_path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False


def append_file_safe(file_path: Path, content: str) -> bool:
    """Safely append content to file with error handling."""
    try:
        ensure_directory(file_path.parent)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False


def generate_unique_filename(directory: Path, base_name: str, extension: str) -> str:
    """Generate a unique filename to avoid conflicts."""
    counter = 1
    filename = f"{base_name}.{extension}"
    
    while (directory / filename).exists():
        filename = f"{base_name}_{counter}.{extension}"
        counter += 1
    
    return filename