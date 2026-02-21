"""
Supabase Storage Helper
Handles file uploads and URL generation for Supabase Storage
Falls back to local storage if Supabase is not configured
"""
import os
from werkzeug.utils import secure_filename
import time

# Try to import Supabase and config
try:
    from supabase import create_client, Client
    SUPABASE_LIB_AVAILABLE = True
except ImportError:
    SUPABASE_LIB_AVAILABLE = False
    print("⚠️  Supabase library not installed - using local storage only")

try:
    import config
except ImportError:
    print("⚠️  config.py not found - using local storage only")
    # Create mock config
    class MockConfig:
        SUPABASE_URL = "YOUR_SUPABASE_URL"
        SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
    config = MockConfig()

# Check if Supabase is configured
SUPABASE_ENABLED = False
supabase = None

if SUPABASE_LIB_AVAILABLE:
    try:
        SUPABASE_ENABLED = (
            hasattr(config, 'SUPABASE_URL') and 
            hasattr(config, 'SUPABASE_KEY') and
            config.SUPABASE_URL != "YOUR_SUPABASE_URL" and
            config.SUPABASE_KEY != "YOUR_SUPABASE_ANON_KEY"
        )
        
        if SUPABASE_ENABLED:
            supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            print("✅ Supabase Storage enabled")
        else:
            print("⚠️  Supabase not configured - using local storage")
    except Exception as e:
        SUPABASE_ENABLED = False
        supabase = None
        print(f"⚠️  Supabase initialization error - using local storage: {e}")

def upload_file(file, bucket_name, folder="", local_folder="static"):
    """
    Upload a file to Supabase Storage (or local if not configured)
    
    Args:
        file: FileStorage object from Flask request
        bucket_name: Name of the storage bucket
        folder: Optional folder within bucket
        local_folder: Fallback local folder if Supabase not configured
    
    Returns:
        str: Path/URL of uploaded file or None if failed
    """
    global SUPABASE_ENABLED
    
    if not file or not file.filename:
        return None
    
    filename = secure_filename(file.filename)
    timestamp = str(int(time.time()))
    unique_filename = f"{timestamp}_{filename}"
    
    if SUPABASE_ENABLED and supabase:
        # Upload to Supabase Storage
        path = f"{folder}/{unique_filename}" if folder else unique_filename
        
        try:
            # Read file data
            file.seek(0)  # Reset file pointer
            file_data = file.read()
            
            # Upload to Supabase Storage
            result = supabase.storage.from_(bucket_name).upload(
                path=path,
                file=file_data,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
            
            # Return path (templates will use get_file_url to get full URL)
            return f"{bucket_name}/{path}"
            
        except Exception as e:
            print(f"Supabase upload error: {e}")
            # Fall back to local storage on error
            SUPABASE_ENABLED = False
    
    # Local storage fallback
    local_path = os.path.join(local_folder, bucket_name)
    os.makedirs(local_path, exist_ok=True)
    
    filepath = os.path.join(local_path, unique_filename)
    file.seek(0)  # Reset file pointer
    file.save(filepath)
    
    # Return relative path from static folder
    return f"{bucket_name}/{unique_filename}"

def get_public_url(path, bucket_name):
    """
    Get public URL for a file in Supabase Storage
    
    Args:
        path: File path in bucket (e.g., "avatars/123_image.jpg")
        bucket_name: Name of the storage bucket
    
    Returns:
        str: Public URL or local path
    """
    if not path:
        return None
    
    # If Supabase is enabled, get public URL
    if SUPABASE_ENABLED and supabase:
        try:
            # Remove bucket name from path if it's included
            clean_path = path.replace(f"{bucket_name}/", "")
            return supabase.storage.from_(bucket_name).get_public_url(clean_path)
        except Exception as e:
            print(f"Error getting public URL: {e}")
    
    # Return local static path
    return f"/static/{path}"

def get_file_url(path):
    """
    Helper to get file URL - determines bucket from path
    
    Args:
        path: File path like "avatars/123_image.jpg"
    
    Returns:
        str: Full URL for file
    """
    if not path:
        return None
    
    # Extract bucket name from path
    if '/' in path:
        bucket = path.split('/')[0]
        return get_public_url(path, bucket)
    
    return f"/static/{path}"

def delete_file(path, bucket_name):
    """
    Delete a file from Supabase Storage (or local)
    
    Args:
        path: File path in bucket
        bucket_name: Name of the storage bucket
    
    Returns:
        bool: True if successful
    """
    if not path:
        return False
    
    if SUPABASE_ENABLED and supabase:
        try:
            clean_path = path.replace(f"{bucket_name}/", "")
            supabase.storage.from_(bucket_name).remove([clean_path])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    # Local storage - delete file
    try:
        local_path = os.path.join("static", path)
        if os.path.exists(local_path):
            os.remove(local_path)
            return True
    except Exception as e:
        print(f"Local delete error: {e}")
    
    return False

# Helper functions for specific buckets
def upload_avatar(file):
    """Upload avatar to avatars bucket"""
    try:
        bucket = config.BUCKET_AVATARS if hasattr(config, 'BUCKET_AVATARS') else "avatars"
    except:
        bucket = "avatars"
    return upload_file(file, bucket)

def upload_post_image(file):
    """Upload post image to uploads bucket"""
    try:
        bucket = config.BUCKET_UPLOADS if hasattr(config, 'BUCKET_UPLOADS') else "uploads"
    except:
        bucket = "uploads"
    return upload_file(file, bucket)

def upload_music_file(file):
    """Upload music to music bucket"""
    try:
        bucket = config.BUCKET_MUSIC if hasattr(config, 'BUCKET_MUSIC') else "music"
    except:
        bucket = "music"
    return upload_file(file, bucket)

def upload_story(file):
    """Upload story to stories bucket"""
    try:
        bucket = config.BUCKET_STORIES if hasattr(config, 'BUCKET_STORIES') else "stories"
    except:
        bucket = "stories"
    return upload_file(file, bucket)

def upload_photo(file):
    """Upload photo to images bucket"""
    try:
        bucket = config.BUCKET_IMAGES if hasattr(config, 'BUCKET_IMAGES') else "images"
    except:
        bucket = "images"
    return upload_file(file, bucket)
