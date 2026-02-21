"""Database schema that works for both SQLite and PostgreSQL"""
import os

# Detect database type
USE_POSTGRES = bool(os.environ.get("DATABASE_URL"))

# Primary key syntax
PK = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

#Boolean type
BOOL = "BOOLEAN" if USE_POSTGRES else "INTEGER"

# Schema definitions
TABLES = {
    "users": f"""
        CREATE TABLE IF NOT EXISTS users (
            id {PK},
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            bio TEXT,
            avatar TEXT,
            verified {BOOL} DEFAULT 0,
            subscription TEXT DEFAULT 'none',
            wallet_balance REAL DEFAULT 0.0,
            handle TEXT UNIQUE,
            badge TEXT DEFAULT 'none',
            is_private {BOOL} DEFAULT 0,
            allow_messages {BOOL} DEFAULT 1,
            hide_followers {BOOL} DEFAULT 0,
            verification_code TEXT,
            is_verified {BOOL} DEFAULT 0,
            is_approved {BOOL} DEFAULT 1,
            verification_sent_at TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            about_me TEXT DEFAULT '',
            interests TEXT DEFAULT ''
        )
    """,
    
    "posts": f"""
        CREATE TABLE IF NOT EXISTS posts (
            id {PK},
            user_id INTEGER,
            content TEXT,
            image TEXT,
            music TEXT,
            music_title TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "profile_posts": f"""
        CREATE TABLE IF NOT EXISTS profile_posts (
            id {PK},
            user_id INTEGER,
            content TEXT,
            image TEXT,
            music TEXT,
            music_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "likes": f"""
        CREATE TABLE IF NOT EXISTS likes (
            id {PK},
            post_id INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
    """,
    
    "messages": f"""
        CREATE TABLE IF NOT EXISTS messages (
            id {PK},
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            sticker TEXT,
            money_amount REAL,
            image TEXT,
            music TEXT,
            music_title TEXT,
            is_read {BOOL} DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "notifications": f"""
        CREATE TABLE IF NOT EXISTS notifications (
            id {PK},
            user_id INTEGER,
            from_user INTEGER,
            type TEXT,
            content TEXT,
            is_read {BOOL} DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "applications": f"""
        CREATE TABLE IF NOT EXISTS applications (
            id {PK},
            user_id INTEGER,
            application_type TEXT,
            reason TEXT,
            experience TEXT,
            contact TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "friendships": f"""
        CREATE TABLE IF NOT EXISTS friendships (
            id {PK},
            user_id INTEGER,
            friend_id INTEGER,
            status TEXT DEFAULT 'pending',
            UNIQUE(user_id, friend_id)
        )
    """,
    
    "followers": f"""
        CREATE TABLE IF NOT EXISTS followers (
            id {PK},
            follower_id INTEGER,
            following_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )
    """,
    
    "comments": f"""
        CREATE TABLE IF NOT EXISTS comments (
            id {PK},
            post_id INTEGER,
            user_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "stories": f"""
        CREATE TABLE IF NOT EXISTS stories (
            id {PK},
            user_id INTEGER,
            content TEXT,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "products": f"""
        CREATE TABLE IF NOT EXISTS products (
            id {PK},
            user_id INTEGER,
            name TEXT,
            description TEXT,
            images TEXT,
            file TEXT,
            type TEXT,
            price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "music_library": f"""
        CREATE TABLE IF NOT EXISTS music_library (
            id {PK},
            user_id INTEGER,
            title TEXT,
            filename TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "album_images": f"""
        CREATE TABLE IF NOT EXISTS album_images (
            id {PK},
            user_id INTEGER,
            image TEXT,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "transactions": f"""
        CREATE TABLE IF NOT EXISTS transactions (
            id {PK},
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "purchases": f"""
        CREATE TABLE IF NOT EXISTS purchases (
            id {PK},
            user_id INTEGER,
            product_id INTEGER,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "blocked_users": f"""
        CREATE TABLE IF NOT EXISTS blocked_users (
            id {PK},
            user_id INTEGER,
            blocked_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, blocked_user_id)
        )
    """,
    
    "watch_rooms": f"""
        CREATE TABLE IF NOT EXISTS watch_rooms (
            id {PK},
            host_id INTEGER,
            room_name TEXT,
            video_id TEXT,
            current_time REAL DEFAULT 0,
            is_playing {BOOL} DEFAULT 0,
            is_active {BOOL} DEFAULT 1,
            is_private {BOOL} DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "watch_participants": f"""
        CREATE TABLE IF NOT EXISTS watch_participants  (
            id {PK},
            room_id INTEGER,
            user_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_id, user_id)
        )
    """
}
