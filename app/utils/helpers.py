import re
from werkzeug.utils import secure_filename

def sanitize_filename(filename):
    """Sanitizes file names to prevent directory traversal and special character errors.
    
    Replaces restricted file character patterns with underscores, limits length,
    and falls back to a safe filename if empty.
    """
    if not filename:
        return "shared_file"
        
    # Standard replacement for special OS path tokens
    cleaned = re.sub(r'[<>\:"/\\|?*]', '_', filename)
    
    # Use werkzeug helper as a secondary filter
    cleaned = secure_filename(cleaned)
    
    if not cleaned.strip() or cleaned == "..":
        cleaned = "shared_file"
        
    return cleaned[:150]

def format_size(bytes_count):
    """Converts raw byte counts into human readable formats."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1048576:
        return f"{(bytes_count / 1024):.1f} KB"
    elif bytes_count < 1073741824:
        return f"{(bytes_count / 1048576):.1f} MB"
    return f"{(bytes_count / 1073741824):.2f} GB"
