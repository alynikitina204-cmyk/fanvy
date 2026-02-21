"""
Supabase Configuration Template
Copy this file to config.py and fill in your Supabase credentials

For deployment on Render:
- Set these as Environment Variables instead (SUPABASE_URL and SUPABASE_KEY)
- This file is only needed for local development
"""

# Get these from your Supabase project dashboard
# https://app.supabase.com/ -> Your Project -> Settings -> API

SUPABASE_URL = "YOUR_SUPABASE_URL"  # e.g., "https://xxxxx.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"  # Public anon key (safe for client-side)

# Storage bucket names (default names, will be created in Supabase)
BUCKET_AVATARS = "avatars"
BUCKET_UPLOADS = "uploads"
BUCKET_MUSIC = "music"
BUCKET_STORIES = "stories"
BUCKET_IMAGES = "images"
