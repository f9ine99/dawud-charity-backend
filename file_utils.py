import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
import mimetypes
try:
    from PIL import Image
except ImportError:
    import Image
import aiofiles

# Allowed file types
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Upload directories
UPLOAD_DIR = Path("uploads")
SECURE_UPLOAD_DIR = UPLOAD_DIR / "donations"
TEMP_DIR = Path("temp")

def ensure_directories():
    """Ensure all necessary directories exist."""
    for directory in [UPLOAD_DIR, SECURE_UPLOAD_DIR, TEMP_DIR]:
        directory.mkdir(exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Remove any path separators and dangerous characters
    filename = os.path.basename(filename)
    # Keep only alphanumeric, dots, hyphens, and underscores
    filename = ''.join(c for c in filename if c.isalnum() or c in '.-_')
    # Default to jpg if no filename
    if not filename:
        return 'unnamed_file.jpg'
    # Ensure it has an extension
    if '.' not in filename:
        return f"{filename}.jpg"
    return filename

def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure, randomized filename."""
    # Get file extension
    _, ext = os.path.splitext(original_filename.lower())

    # Ensure it's an allowed extension
    if ext not in ALLOWED_EXTENSIONS:
        ext = '.jpg'  # Default to jpg if unknown

    # Generate random filename
    random_name = str(uuid.uuid4())
    return f"{random_name}{ext}"

def validate_image_file(file_path: str) -> bool:
    """Validate that the file is actually a valid image (JPG or PNG)."""
    try:
        with Image.open(file_path) as img:
            # Check if it's a JPEG or PNG
            if img.format not in ['JPEG', 'JPG', 'PNG']:
                return False

            # Optional: Check image dimensions/sanity
            if img.width > 10000 or img.height > 10000:  # Reasonable size limit
                return False

            return True
    except Exception:
        return False

async def save_upload_file_securely(file, filename: str) -> Optional[str]:
    """Save uploaded file with security measures."""
    try:
        # Generate secure filename
        secure_filename = generate_secure_filename(filename)

        # Create temporary file path
        temp_path = TEMP_DIR / secure_filename

        # Save file temporarily and check size
        async with aiofiles.open(temp_path, 'wb') as buffer:
            content = await file.read()
            
            # Check file size
            if len(content) > MAX_FILE_SIZE:
                raise ValueError(f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB")
            
            await buffer.write(content)

        # Validate the saved file
        if not validate_image_file(str(temp_path)):
            # Remove invalid file
            if temp_path.exists():
                temp_path.unlink()
            return None

        # Move to secure location
        final_path = SECURE_UPLOAD_DIR / secure_filename
        shutil.move(str(temp_path), str(final_path))

        # Return relative path for database storage
        return f"donations/{secure_filename}"

    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
        raise e

def get_file_path(image_path: str) -> Optional[Path]:
    """Get the full file path for serving files."""
    if not image_path:
        return None

    # Ensure path doesn't escape our upload directory
    path = Path(image_path)
    if path.is_absolute() or '..' in path.parts:
        return None

    full_path = UPLOAD_DIR / path
    if not full_path.exists():
        return None

    return full_path

def cleanup_temp_files():
    """Clean up temporary files (call periodically)."""
    if TEMP_DIR.exists():
        for file_path in TEMP_DIR.glob("*"):
            try:
                if file_path.is_file():
                    file_path.unlink()
            except Exception:
                pass
