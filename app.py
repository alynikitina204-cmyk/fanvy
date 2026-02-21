from flask import Flask, render_template, request, redirect, session, jsonify, flash
from markupsafe import Markup
import sqlite3, os, uuid, re
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_socketio import SocketIO, emit, join_room  # Disabled for deployment
import storage  # Storage integration (Supabase or local)
import email_service  # Email sending service

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")
ADMIN_EMAIL = "ho.swag@mail.ru"

# socketio = SocketIO(app, cors_allowed_origins="*")  # Disabled for deployment

# Jinja filter for file URLs (Supabase or local)
@app.template_filter('file_url')
def file_url_filter(path):
    """Convert file path to proper URL (Supabase or local static/)"""
    if not path:
        return None
    return storage.get_file_url(path)

# Register the filter
app.jinja_env.filters['file_url'] = file_url_filter

# -----------------------
# Notification Counts Context Processor
# -----------------------
@app.context_processor
def inject_notifications():
    """Make notification counts available to all templates"""
    if 'user_id' not in session:
        return dict(
            unread_messages_count=0,
            friend_requests_count=0,
            new_followers_count=0
        )
    
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        
        # Count unread messages
        try:
            unread_messages = conn.execute("""
                SELECT COUNT(*) as count FROM messages 
                WHERE receiver_id=? AND is_read=0
            """, (user_id,)).fetchone()
            unread_messages_count = unread_messages['count'] if unread_messages else 0
        except sqlite3.OperationalError:
            # Column might not exist yet during database migration
            unread_messages_count = 0
        
        # Count pending friend requests (received, not sent)
        try:
            friend_requests = conn.execute("""
                SELECT COUNT(*) as count FROM friendships 
                WHERE friend_id=? AND status='pending'
            """, (user_id,)).fetchone()
            friend_requests_count = friend_requests['count'] if friend_requests else 0
        except sqlite3.OperationalError:
            friend_requests_count = 0
        
        # Count new followers (last 7 days) - only for users with subscription
        new_followers_count = 0
        try:
            user = conn.execute("SELECT subscription FROM users WHERE id=?", (user_id,)).fetchone()
            if user and user['subscription'] in ['basic', 'pro', 'premium']:
                new_followers = conn.execute("""
                    SELECT COUNT(*) as count FROM followers 
                    WHERE following_id=? AND created_at >= datetime('now', '-7 days')
                """, (user_id,)).fetchone()
                new_followers_count = new_followers['count'] if new_followers else 0
        except:
            pass
        
        conn.close()
        
        return dict(
            unread_messages_count=unread_messages_count,
            friend_requests_count=friend_requests_count,
            new_followers_count=new_followers_count
        )
    except Exception as e:
        print(f"⚠️  Error in inject_notifications: {e}")
        return dict(
            unread_messages_count=0,
            friend_requests_count=0,
            new_followers_count=0
        )

# -----------------------
# Online Status Tracking
# -----------------------
def update_user_activity(user_id):
    """Update user's last_activity timestamp"""
    try:
        conn = get_db_connection()
        conn.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def is_user_online(user_id):
    """Check if user is online (active in last 5 minutes)"""
    try:
        # Handle None or invalid user_id
        if not user_id:
            return False
        user_id = int(user_id) if isinstance(user_id, str) else user_id
        
        conn = get_db_connection()
        user = conn.execute("""
            SELECT last_activity FROM users WHERE id=?
        """, (user_id,)).fetchone()
        conn.close()
        
        if not user or not user['last_activity']:
            return False
        
        from datetime import datetime, timedelta
        last_activity = datetime.fromisoformat(user['last_activity'])
        return datetime.now() - last_activity < timedelta(minutes=5)
    except Exception as e:
        return False

# Jinja filter for online status
@app.template_filter('online_status')
def online_status_filter(user_id):
    """Return HTML for online status indicator"""
    try:
        # Handle None or empty values
        if not user_id:
            return Markup('')
        # Convert to int if it's a string
        user_id = int(user_id) if isinstance(user_id, str) else user_id
        if is_user_online(user_id):
            return Markup('<span class="online-badge" title="Online">●</span>')
        return Markup('')  # Show nothing for offline
    except (ValueError, TypeError, AttributeError):
        return Markup('')

# Register online filter
app.jinja_env.filters['online_status'] = online_status_filter

# Linkify filter - convert URLs to clickable links
@app.template_filter('linkify')
def linkify_filter(text):
    """Convert URLs in text to clickable links"""
    if not text:
        return ''
    
    # Regex pattern to match URLs
    url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
    
    def replace_url(match):
        url = match.group(1)
        # Remove trailing punctuation that's likely not part of the URL
        while url and url[-1] in '.,;:!?)':
            url = url[:-1]
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">{url}</a>'
    
    # Replace URLs with anchor tags
    linked_text = re.sub(url_pattern, replace_url, text)
    
    # Preserve line breaks
    linked_text = linked_text.replace('\n', '<br>')
    
    return Markup(linked_text)

app.jinja_env.filters['linkify'] = linkify_filter

# Track user activity
@app.before_request
def track_activity():
    """Update user's last_activity on each request"""
    if "user_id" in session:
        update_user_activity(session["user_id"])

# -----------------------
# Delete profile post
@app.route("/profile/post/<int:post_id>/delete", methods=["POST"])
def delete_profile_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM profile_posts WHERE id=? AND user_id=?",
        (post_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    
    # Redirect to photos if coming from there, otherwise profile
    referer = request.headers.get('Referer', '')
    if '/photos' in referer:
        return redirect("/photos")
    return redirect("/profile")

# -----------------------
# Delete Account (complete user deletion)
@app.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect("/login")
    
    user_id = session["user_id"]
    conn = get_db_connection()
    
    try:
        # Delete all user data from all tables
        conn.execute("DELETE FROM profile_posts WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM posts WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM comments WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM likes WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM stories WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM album_images WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM products WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM purchases WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM music_library WHERE user_id=?", (user_id,))
        
        # Delete friendships (both directions)
        conn.execute("DELETE FROM friendships WHERE user_id=? OR friend_id=?", (user_id, user_id))
        
        # Delete messages (both sent and received)
        conn.execute("DELETE FROM messages WHERE sender_id=? OR receiver_id=?", (user_id, user_id))
        
        # Delete notifications
        try:
            conn.execute("DELETE FROM notifications WHERE user_id=? OR from_user_id=?", (user_id, user_id))
        except sqlite3.OperationalError:
            pass  # Table might not exist or column names different
        
        # Delete group memberships
        try:
            conn.execute("DELETE FROM group_members WHERE user_id=?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Table might not exist
        
        # Delete owned groups
        try:
            conn.execute("DELETE FROM groups WHERE owner_id=?", (user_id,))
        except sqlite3.OperationalError:
            pass  # Table might not exist or column name different
        
        # Finally, delete the user account itself
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error deleting account: {e}")
        conn.close()
        return redirect("/profile?error=delete_failed")
    finally:
        conn.close()
    
    # Clear session and redirect to login
    session.clear()
    return redirect("/login?deleted=1")

# Upload folders
# -----------------------
AVATAR_FOLDER = "static/avatars"
UPLOAD_FOLDER = "static/uploads"
STORY_FOLDER  = "static/stories"
MUSIC_FOLDER  = "static/music"
PRODUCT_FOLDER = "static/products"

ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif","mp3","wav","ogg","m4a",
                      "apk","zip","exe","pdf","py","js","docx","pptx"}

for folder in [AVATAR_FOLDER, UPLOAD_FOLDER, STORY_FOLDER, MUSIC_FOLDER, PRODUCT_FOLDER]:
    os.makedirs(folder, exist_ok=True)


# -----------------------
# Utils
# -----------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_subscription(conn, user_id):
    row = conn.execute(
        "SELECT subscription FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    return (row["subscription"] if row and row["subscription"] else "none")

# -----------------------
# Database
# -----------------------
def create_tables():
    # On first startup in production, ensure fresh database with correct schema
    if os.environ.get("RENDER") and os.path.exists("users.db"):
        try:
            # Check if database has correct schema
            conn = sqlite3.connect("users.db")
            cursor = conn.execute("PRAGMA table_info(messages)")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()
            
            # If is_read column missing, recreate database
            if "is_read" not in columns:
                print("⚠️  Old database schema detected, recreating...")
                os.remove("users.db")
        except:
            pass
    
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS album_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image TEXT,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT,
        bio TEXT,
        avatar TEXT,
        verified INTEGER DEFAULT 0,
        subscription TEXT DEFAULT 'none',
        wallet_balance REAL DEFAULT 0.0,
        handle TEXT UNIQUE,
        badge TEXT DEFAULT 'none',
        is_private INTEGER DEFAULT 0,
        allow_messages INTEGER DEFAULT 1,
        hide_followers INTEGER DEFAULT 0,
        verification_code TEXT,
        is_verified INTEGER DEFAULT 0,
        is_approved INTEGER DEFAULT 1,
        verification_sent_at TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        about_me TEXT DEFAULT '',
        interests TEXT DEFAULT ''
    )""")
    try:
        conn.execute("ALTER TABLE users ADD COLUMN subscription TEXT DEFAULT 'none'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN wallet_balance REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN handle TEXT")
        # Set handle for existing users who don't have one (only runs if column was just created)
        conn.execute("UPDATE users SET handle = LOWER(REPLACE(username, ' ', '_')) WHERE handle IS NULL")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN badge TEXT DEFAULT 'none'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_private INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN allow_messages INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN hide_followers INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN about_me TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN interests TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    # Update any null values
    try:
        conn.execute("UPDATE users SET handle = LOWER(REPLACE(username, ' ', '_')) WHERE handle IS NULL OR handle = ''")
    except:
        pass
    conn.execute("UPDATE users SET subscription='none' WHERE subscription IS NULL")
    conn.execute("UPDATE users SET wallet_balance=0.0 WHERE wallet_balance IS NULL")
    conn.execute("UPDATE users SET badge='none' WHERE badge IS NULL OR badge = ''")
    conn.execute("UPDATE users SET is_private=0 WHERE is_private IS NULL")
    conn.execute("UPDATE users SET allow_messages=1 WHERE allow_messages IS NULL")
    conn.execute("UPDATE users SET hide_followers=0 WHERE hide_followers IS NULL")
    conn.execute("UPDATE users SET is_verified=0 WHERE is_verified IS NULL")
    conn.execute("UPDATE users SET is_approved=1 WHERE is_approved IS NULL")
    conn.execute("UPDATE users SET about_me='' WHERE about_me IS NULL")
    conn.execute("UPDATE users SET interests='' WHERE interests IS NULL")
    
    # Give admin $1000 for testing and verify/approve admin
    conn.execute("UPDATE users SET wallet_balance=1000.0, is_verified=1, is_approved=1 WHERE id=1")
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        image TEXT,
        music TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS profile_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Add music and music_title to posts and profile_posts
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN music_title TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE profile_posts ADD COLUMN music TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE profile_posts ADD COLUMN music_title TEXT")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
    CREATE TABLE IF NOT EXISTS stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            description TEXT,
            images TEXT,
            file TEXT,
            type TEXT,
            price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS music_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            filename TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    # migrations for older schemas
    try:
        conn.execute("ALTER TABLE products ADD COLUMN images TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE products ADD COLUMN file TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE products ADD COLUMN type TEXT")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS friendships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        friend_id INTEGER,
        status TEXT DEFAULT 'pending',
        UNIQUE(user_id, friend_id)
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(follower_id, following_id)
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT,
        sticker TEXT,
        money_amount REAL,
        image TEXT,
        music TEXT,
        music_title TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN sticker TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN money_amount REAL")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN image TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN music TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN music_title TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        from_user INTEGER,
        type TEXT,
        content TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS blocked_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        blocked_user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, blocked_user_id)
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS watch_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host_id INTEGER,
        room_name TEXT,
        video_id TEXT,
        current_time REAL DEFAULT 0,
        is_playing INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        is_private INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS watch_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        user_id INTEGER,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_id, user_id)
    )""")
    
    # Add is_private column if it doesn't exist
    try:
        conn.execute("ALTER TABLE watch_rooms ADD COLUMN is_private INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

# Initialize database with error handling
try:
    create_tables()
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"❌ Error creating database tables: {e}")
    import traceback
    traceback.print_exc()

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    import traceback
    error_details = traceback.format_exc()
    print(f"❌ Internal Server Error: {error_details}")
    return f"<h1>Internal Server Error</h1><pre>{error_details}</pre>", 500

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    error_details = traceback.format_exc()
    print(f"❌ Unhandled Exception: {error_details}")
    return f"<h1>Error</h1><pre>{error_details}</pre>", 500

# -----------------------
# Auth
# -----------------------
@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        action = request.form.get("action", "register")
        email = request.form.get("email")
        
        if action == "register":
            # Check registration limit (100 users max)
            conn = get_db_connection()
            user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
            
            if user_count >= 100:
                conn.close()
                flash("Registration is currently closed. Maximum user limit reached.", "error")
                return render_template("register.html", user_count=user_count, spots_remaining=0)
            
            # Step 1: Create account and send verification code
            username = request.form.get("username")
            password = request.form.get("password")
            about_me = request.form.get("about_me", "")
            handle = username.lower().replace(" ", "_")
            
            # Generate 6-digit verification code
            import random
            verification_code = str(random.randint(100000, 999999))
            
            # First user is auto-approved as admin, others need approval
            is_approved = 1 if user_count == 0 else 0
            
            try:
                conn.execute("""
                    INSERT INTO users (username, email, password, handle, about_me, verification_code, is_verified, is_approved, verification_sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
                """, (
                    username,
                    email,
                    generate_password_hash(password),
                    handle,
                    about_me,
                    verification_code,
                    is_approved
                ))
                conn.commit()
                
                # Send verification email
                email_sent = email_service.send_verification_email(email, username, verification_code)
                
                # Store email in session for verification step
                session["pending_verification_email"] = email
                if not email_sent:
                    # If email not configured, show code on screen for testing
                    session["verification_code"] = verification_code
                
                conn.close()
                
                if email_sent:
                    flash(f"Verification code sent to {email}! Check your inbox.", "success")
                else:
                    flash(f"Email not configured. Your code: {verification_code}", "success")
                
                return redirect("/verify")
                
            except sqlite3.IntegrityError:
                conn.close()
                flash("Username or email already exists", "error")
                return render_template("register.html", user_count=user_count, spots_remaining=max(0, 100 - user_count))
        
    # GET request - show registration form with available spots
    conn = get_db_connection()
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    conn.close()
    spots_remaining = max(0, 100 - user_count)
    return render_template("register.html", user_count=user_count, spots_remaining=spots_remaining)

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        code = request.form.get("code")
        email = session.get("pending_verification_email")
        
        if not email:
            flash("Verification session expired. Please register again.", "error")
            return redirect("/register")
        
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND verification_code=?",
            (email, code)
        ).fetchone()
        
        if user:
            # Mark as verified
            conn.execute(
                "UPDATE users SET is_verified=1, verification_code=NULL WHERE email=?",
                (email,)
            )
            conn.commit()
            conn.close()
            
            # Clear session
            session.pop("pending_verification_email", None)
            session.pop("verification_code", None)
            
            if user["is_approved"] == 0:
                flash("Account verified! Waiting for admin approval.", "success")
                return redirect("/login")
            else:
                flash("Account verified! You can now login.", "success")
                return redirect("/login")
        else:
            conn.close()
            flash("Invalid verification code", "error")
    
    return render_template("verify.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=?",
                            (request.form["email"],)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):
            # Check if verified
            if user["is_verified"] == 0:
                flash("Please verify your email first. Check your inbox for the verification code.", "error")
                return render_template("login.html")
            
            # Check if approved
            if user["is_approved"] == 0:
                flash("Your account is pending admin approval.", "error")
                return render_template("login.html")
            
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            return redirect("/forum")
        
        flash("Invalid email or password", "error")
        return render_template("login.html")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/dashboard")

# -----------------------
# Admin User Management
# -----------------------
@app.route("/admin/approvals")
def admin_approvals():
    if "user_id" not in session or session.get("user_id") != 1:
        flash("Admin access only", "error")
        return redirect("/forum")
    
    conn = get_db_connection()
    
    # Get users pending approval
    pending = conn.execute("""
        SELECT id, username, email, created_at, is_verified
        FROM users
        WHERE is_approved = 0
        ORDER BY created_at DESC
    """).fetchall()
    
    # Get all users for management
    all_users = conn.execute("""
        SELECT id, username, email, is_verified, is_approved, subscription, created_at
        FROM users
        ORDER BY created_at DESC
    """).fetchall()
    
    conn.close()
    
    return render_template("admin_approvals.html", pending=pending, all_users=all_users)

@app.route("/admin/approve_user/<int:user_id>", methods=["POST"])
def approve_user(user_id):
    if "user_id" not in session or session.get("user_id") != 1:
        return jsonify({"error": "Admin only"}), 403
    
    conn = get_db_connection()
    conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User approved successfully!", "success")
    return redirect("/admin/approvals")

@app.route("/admin/reject_user/<int:user_id>", methods=["POST"])
def reject_user(user_id):
    if "user_id" not in session or session.get("user_id") != 1:
        return jsonify({"error": "Admin only"}), 403
    
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id=? AND is_approved=0", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User rejected and removed", "success")
    return redirect("/admin/approvals")

# -----------------------
# Dashboard
# -----------------------
@app.route("/dashboard")
def dashboard():
    
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    friend_count = conn.execute("""
        SELECT COUNT(*) FROM friendships
        WHERE (user_id=? OR friend_id=?)
        AND status='accepted'
    """,(session["user_id"], session["user_id"])).fetchone()[0]

    post_count = conn.execute("""
        SELECT COUNT(*) FROM posts WHERE user_id=?
    """,(session["user_id"],)).fetchone()[0]

    story_count = conn.execute("""
        SELECT COUNT(*) FROM stories WHERE user_id=?
    """,(session["user_id"],)).fetchone()[0]

    # For admin: get pending applications count
    pending_apps = 0
    pending_users = 0
    if session.get("user_id") == 1:
        pending_apps = conn.execute("""
            SELECT COUNT(*) FROM applications WHERE status='pending'
        """).fetchone()[0]
        
        pending_users = conn.execute("""
            SELECT COUNT(*) FROM users WHERE is_approved=0 AND is_verified=1
        """).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        username=user['username'] if user else session.get('username', 'User'),
        user=user,
        friend_count=friend_count,
        post_count=post_count,
        story_count=story_count,
        pending_apps=pending_apps,
        pending_users=pending_users
    )

@app.route("/admin/pending-users")
def pending_users():
    if "user_id" not in session:
        return redirect("/login")
    
    # Admin only
    if session.get("user_id") != 1:
        return redirect("/dashboard")
    
    conn = get_db_connection()
    
    # Get all pending users (verified but not approved)
    users = conn.execute("""
        SELECT id, username, email, handle, about_me, verification_sent_at, is_verified
        FROM users
        WHERE is_approved=0 AND is_verified=1
        ORDER BY verification_sent_at DESC
    """).fetchall()
    
    conn.close()
    
    return render_template("pending_users.html", users=users)

@app.route("/admin/approve-user/<int:user_id>", methods=["POST"])
def approve_pending_user(user_id):
    if "user_id" not in session or session.get("user_id") != 1:
        return redirect("/login")
    
    conn = get_db_connection()
    conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User approved successfully!", "success")
    return redirect("/admin/pending-users")

@app.route("/admin/reject-user/<int:user_id>", methods=["POST"])
def reject_pending_user(user_id):
    if "user_id" not in session or session.get("user_id") != 1:
        return redirect("/login")
    
    conn = get_db_connection()
    
    # Delete the user completely
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User rejected and removed.", "success")
    return redirect("/admin/pending-users")

@app.route("/search", methods=["GET", "POST"])
def search():
    if "user_id" not in session:
        return redirect("/login")

    results = []
    query = ""

    if request.method == "POST":
        query = request.form.get("query", "").strip()

        conn = get_db_connection()
        results = conn.execute(
            "SELECT id, username, avatar, subscription FROM users WHERE username LIKE ? AND id != ?",
            (f"%{query}%", session["user_id"])
        ).fetchall()
        conn.close()

    return render_template("search.html", results=results, query=query)


# -----------------------
# Community / Forum
# -----------------------
@app.route("/forum", methods=["GET","POST"])
def forum():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    user = conn.execute("SELECT * FROM users WHERE id=?",
                        (session["user_id"],)).fetchone()

    if request.method == "POST":
        content = request.form.get("content","").strip()
        tags = request.form.get("tags","").strip()
        image = request.files.get("image")
        music = request.files.get("music")

        filename = None
        music_name = None
        music_title = None
        
        if image and image.filename and allowed_file(image.filename):
            filename = storage.upload_post_image(image)

        if music and music.filename and allowed_file(music.filename):
            # Store the original filename
            music_title = music.filename
            music_name = storage.upload_music_file(music)

        if content or filename or music_name:
            conn.execute("""
                INSERT INTO posts (user_id,content,image,music,music_title,tags)
                VALUES (?,?,?,?,?,?)
            """,(session["user_id"], content, filename, music_name, music_title, tags))
            conn.commit()
            return redirect("/forum")

    # Get user interests for personalized feed
    user_interests = user["interests"] or ""
    user_interests_list = [i.strip().lower() for i in user_interests.split(",") if i.strip()]
    
    posts = conn.execute("""
        SELECT posts.*, users.username, users.avatar, users.subscription AS user_subscription, users.badge AS user_badge,
        (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.id) AS like_count
        FROM posts JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """).fetchall()

    final_posts = []
    for p in posts:
        comments = conn.execute("""
            SELECT comments.*, users.username, users.avatar
            FROM comments JOIN users ON comments.user_id = users.id
            WHERE comments.post_id=?
        """,(p["id"],)).fetchall()

        post_dict = {**dict(p), "comments": comments}
        
        # Calculate interest match score
        post_tags = (p["tags"] or "").lower()
        post_tags_list = [t.strip() for t in post_tags.split(",") if t.strip()]
        
        # Count how many user interests match this post's tags
        match_score = sum(1 for interest in user_interests_list 
                         if any(interest in tag or tag in interest for tag in post_tags_list))
        
        post_dict["interest_score"] = match_score
        
        # Premium users get priority
        is_premium = 1 if p["user_subscription"] == "premium" else 0
        post_dict["is_premium"] = is_premium
        
        final_posts.append(post_dict)
    
    # Sort posts: Premium users first, then highest interest match, then by creation date
    final_posts.sort(key=lambda x: (x["is_premium"], x["interest_score"], x["created_at"]), reverse=True)

    stories = conn.execute("""
        SELECT stories.*, users.username, users.avatar, users.subscription AS user_subscription, users.badge AS user_badge
        FROM stories JOIN users ON stories.user_id = users.id
        ORDER BY stories.created_at DESC
    """).fetchall()

    # convert to plain dictionaries and group by user so each circle represents one person
    stories_by_user = {}
    for s in stories:
        sd = dict(s)
        uid = sd["user_id"]
        stories_by_user.setdefault(uid, []).append(sd)

    conn.close()

    return render_template("forum.html",
                           posts=final_posts,
                           stories_by_user=stories_by_user,
                           user=user)

# -----------------------
# Story Upload
# -----------------------
@app.route("/add_story", methods=["POST"])
def add_story():
    if "user_id" not in session:
        return redirect("/login")

    image = request.files.get("image")
    content = request.form.get("content","")

    next_url = request.args.get("next") or "/forum"

    if not image or not allowed_file(image.filename):
        return redirect(next_url)

    filename = storage.upload_story(image)
    if not filename:
        return redirect(next_url)

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO stories (user_id,content,image)
        VALUES (?,?,?)
    """,(session["user_id"], content, filename))
    conn.commit()
    conn.close()

    return redirect(next_url)
@app.route("/story/<int:story_id>/delete", methods=["POST"])
def delete_story(story_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # Only delete YOUR own stories
    conn.execute("""
        DELETE FROM stories 
        WHERE id = ? AND user_id = ?
    """, (story_id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect("/forum")

@app.route("/story/<int:story_id>/reply", methods=["POST"])
def reply_story(story_id):
    if "user_id" not in session:
        return redirect("/login")

    content = request.form.get("content", "").strip()
    if not content:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "empty"}), 400
        return redirect("/forum")

    conn = get_db_connection()
    story = conn.execute(
        "SELECT id, user_id FROM stories WHERE id=?",
        (story_id,)
    ).fetchone()

    if not story:
        conn.close()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "not_found"}), 404
        return redirect("/forum")

    if story["user_id"] == session.get("user_id"):
        conn.close()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"error": "self"}), 400
        return redirect("/forum")

    msg_content = f"Story reply: {content}"
    conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, content, sticker) VALUES (?, ?, ?, ?)",
        (session["user_id"], story["user_id"], msg_content, None)
    )
    conn.commit()
    conn.close()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})

    return redirect(f"/messages/{story['user_id']}")

# -----------------------
# Album Upload
# -----------------------
@app.route("/add_album_image", methods=["POST"])
def add_album_image():
    if "user_id" not in session:
        return redirect("/login")

    image = request.files.get("image")
    caption = request.form.get("caption", "").strip()

    if not image or not allowed_file(image.filename):
        return redirect("/profile")

    image_path = storage.upload_photo(image)
    if not image_path:
        return redirect("/profile")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO album_images (user_id, image, caption) VALUES (?, ?, ?)",
        (session["user_id"], image_path, caption)
    )
    conn.commit()
    conn.close()

    return redirect("/profile")

@app.route("/album/<int:img_id>/delete", methods=["POST"])
def delete_album_image(img_id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM album_images WHERE id=? AND user_id=?",
        (img_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    
    # Redirect to photos if coming from there, otherwise profile
    referer = request.headers.get('Referer', '')
    if '/photos' in referer:
        return redirect("/photos")
    return redirect("/profile")

# -----------------------
# Shop / products
# -----------------------
@app.route("/shop", methods=["GET","POST"])
def shop():
    if "user_id" not in session:
        return redirect("/login")
    
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')

    conn = get_db_connection()
    user_subscription = get_subscription(conn, session.get("user_id"))

    # search support
    query = request.args.get('q','').strip()
    limit_error = request.args.get('limit')

    if request.method == "POST":
        count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE user_id=?",
            (session["user_id"],)
        ).fetchone()[0]

        # Product limits: basic=1, pro=5, premium=unlimited
        limit = None
        if user_subscription == "basic":
            limit = 1
        elif user_subscription == "pro":
            limit = 5
        # premium/none = unlimited (no limit)

        if limit and count >= limit:
            conn.close()
            return redirect(f"/shop?limit={limit}")

        name = request.form.get("name", "").strip()
        description = request.form.get("description", "")
        price = request.form.get("price", "0").strip()
        product_type = request.form.get("product_type", "normal")
        if product_type not in ("normal", "sticker"):
            product_type = "normal"
        main_file = request.files.get("main_file")
        file_path = None
        images = request.files.getlist("images")
        image_paths = []

        # save main file if present
        if main_file and main_file.filename and allowed_file(main_file.filename):
            file_path = storage.upload_file(main_file, "products")

        # save up to 5 images
        for img in images[:5]:
            if img and img.filename and allowed_file(img.filename):
                uploaded_path = storage.upload_file(img, "products")
                if uploaded_path:
                    image_paths.append(uploaded_path)

        images_str = ",".join(image_paths) if image_paths else None

        if name:
            conn.execute(
                """
                INSERT INTO products (user_id, name, description, images, file, type, price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session["user_id"], name, description, images_str, file_path, product_type, price)
            )
            conn.commit()
        return redirect("/shop")

    if query:
        products = conn.execute(
            "SELECT p.*, u.username, u.avatar, u.subscription AS seller_subscription "
            "FROM products p JOIN users u ON p.user_id = u.id "
            "WHERE p.name LIKE ? "
            "ORDER BY p.created_at DESC",
            (f"%{query}%",)
        ).fetchall()
    else:
        products = conn.execute(
            "SELECT p.*, u.username, u.avatar, u.subscription AS seller_subscription "
            "FROM products p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.created_at DESC"
        ).fetchall()

    # load cart count from session
    cart = session.get('cart', [])
    cart_count = len(cart)

    conn.close()
    return render_template(
        "shop.html",
        products=products,
        cart_count=cart_count,
        query=query,
        limit_error=limit_error,
        user_subscription=user_subscription
    )

@app.route('/shop/product/<int:prod_id>/delete', methods=['POST'])
def delete_product(prod_id):
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM products WHERE id=? AND user_id=?",
        (prod_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    return redirect('/shop')

@app.route('/cart/add/<int:prod_id>')
def cart_add(prod_id):
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    cart = session.get('cart', [])
    if prod_id not in cart:
        cart.append(prod_id)
    session['cart'] = cart
    return redirect('/shop')

@app.route('/cart/remove/<int:prod_id>')
def cart_remove(prod_id):
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    cart = session.get('cart', [])
    if prod_id in cart:
        cart.remove(prod_id)
    session['cart'] = cart
    return redirect('/shop')

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    conn = get_db_connection()
    cart = session.get('cart', [])
    products = []
    if cart:
        placeholders = ','.join('?' for _ in cart)
        query = f"SELECT p.*, u.username FROM products p JOIN users u ON p.user_id=u.id WHERE p.id IN ({placeholders})"
        products = conn.execute(query, cart).fetchall()
    conn.close()
    return render_template('cart.html', products=products)

@app.route('/cart/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    
    conn = get_db_connection()
    user = conn.execute("SELECT wallet_balance FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    if not user:
        conn.close()
        return redirect('/login')
    
    cart = session.get('cart', [])
    if not cart:
        conn.close()
        return redirect('/cart?error=empty')
    
    # Get product prices
    placeholders = ','.join('?' for _ in cart)
    query = f"SELECT id, price FROM products WHERE id IN ({placeholders})"
    products = conn.execute(query, cart).fetchall()
    
    total_price = sum(float(p['price']) for p in products)
    
    # Check if user has enough balance
    if float(user['wallet_balance']) < total_price:
        conn.close()
        return redirect('/cart?error=insufficient_funds')
    
    # Deduct from wallet
    conn.execute(
        "UPDATE users SET wallet_balance = wallet_balance - ? WHERE id=?",
        (total_price, session['user_id'])
    )
    
    # Record transaction
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'purchase', ?, ?)",
        (session['user_id'], -total_price, f"Purchased {len(cart)} product(s)")
    )
    
    # Create purchase records
    for prod_id in cart:
        conn.execute(
            "INSERT INTO purchases (user_id, product_id, purchased_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (session['user_id'], prod_id)
        )
    
    conn.commit()
    conn.close()
    
    # Clear cart
    session['cart'] = []
    
    return redirect('/cart?success=1')

@app.route('/subscription/buy/<plan>', methods=['POST'])
def buy_subscription(plan):
    if 'user_id' not in session:
        return redirect('/login')
    
    if plan not in ('basic', 'pro', 'premium'):
        return redirect('/subscription?error=invalid_plan')
    
    prices = {'basic': 4.0, 'pro': 12.0, 'premium': 24.0}
    price = prices[plan]
    
    conn = get_db_connection()
    user = conn.execute(
        "SELECT wallet_balance, subscription FROM users WHERE id=?",
        (session['user_id'],)
    ).fetchone()
    
    if not user:
        conn.close()
        return redirect('/login')
    
    # Check if user already has this subscription
    if user['subscription'] == plan:
        conn.close()
        return redirect('/subscription?error=already_subscribed')
    
    # Check if user has enough balance
    if float(user['wallet_balance']) < price:
        conn.close()
        return redirect('/subscription?error=insufficient_funds')
    
    # Deduct from wallet
    new_balance = float(user['wallet_balance']) - price
    conn.execute(
        "UPDATE users SET wallet_balance=?, subscription=? WHERE id=?",
        (new_balance, plan, session['user_id'])
    )
    
    # Record transaction
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'subscription', ?, ?)",
        (session['user_id'], -price, f"Purchased {plan.capitalize()} subscription")
    )
    
    conn.commit()
    conn.close()
    
    return redirect('/subscription?success=1')

@app.route('/shop/product/<int:prod_id>')
def view_product(prod_id):
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    conn = get_db_connection()
    product = conn.execute(
        "SELECT p.*, u.username, u.avatar, u.subscription AS seller_subscription FROM products p JOIN users u ON p.user_id = u.id WHERE p.id = ?",
        (prod_id,)
    ).fetchone()
    conn.close()
    if not product:
        return "Product not found", 404
    return render_template('product_detail.html', product=product)

@app.route('/subscription')
def subscription():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session['user_id'],)
    ).fetchone()
    
    # Get last subscription purchase date
    last_subscription_tx = conn.execute(
        "SELECT created_at FROM transactions WHERE user_id=? AND type='subscription' ORDER BY created_at DESC LIMIT 1",
        (session['user_id'],)
    ).fetchone()
    
    conn.close()
    
    return render_template('subscription.html', 
                         user=user, 
                         subscription_date=last_subscription_tx['created_at'] if last_subscription_tx else None)

@app.route('/wallet')
def wallet():
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session['user_id'],)
    ).fetchone()
    
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('wallet.html', user=user, transactions=transactions)

# -----------------------
# Applications (VIP, Ambassador, Team)
# -----------------------
@app.route('/submit_application', methods=['POST'])
def submit_application():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'}), 401
    
    application_type = request.form.get('application_type')
    reason = request.form.get('reason')
    experience = request.form.get('experience', '')
    contact = request.form.get('contact', '')
    
    if not application_type or not reason:
        return jsonify({'success': False, 'message': 'Please fill in all required fields'}), 400
    
    # Check if user already has a pending application of this type
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT id FROM applications WHERE user_id=? AND application_type=? AND status='pending'",
        (session['user_id'], application_type)
    ).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'You already have a pending application for this type'}), 400
    
    # Insert application
    conn.execute("""
        INSERT INTO applications (user_id, application_type, reason, experience, contact, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (session['user_id'], application_type, reason, experience, contact))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Application submitted successfully!'})

@app.route('/applications')
def view_applications():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    
    conn = get_db_connection()
    applications = conn.execute("""
        SELECT a.*, u.username, u.email, u.avatar 
        FROM applications a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    """).fetchall()
    
    suggestions = conn.execute("""
        SELECT s.*, u.username, u.email, u.avatar 
        FROM suggestions s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    
    return render_template('applications.html', applications=applications, suggestions=suggestions)

@app.route('/application/<int:app_id>/update', methods=['POST'])
def update_application(app_id):
    if 'user_id' not in session or session.get('user_id') != 1:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    status = request.form.get('status')
    
    if status not in ['approved', 'rejected', 'pending']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    conn = get_db_connection()
    
    # Delete rejected applications instead of updating status
    if status == 'rejected':
        conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Application rejected and deleted'})
    
    # For approved and pending, just update status
    conn.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Application {status}'})

@app.route('/suggest-idea', methods=['GET', 'POST'])
def suggest_idea():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category', 'general')
        
        if not title or not description:
            flash('Please provide both title and description', 'error')
            return render_template('suggest_idea.html')
        
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO suggestions (user_id, title, description, category)
            VALUES (?, ?, ?, ?)
        """, (session['user_id'], title, description, category))
        conn.commit()
        conn.close()
        
        flash('Your idea has been submitted! Thank you for your feedback.', 'success')
        return redirect('/forum')
    
    return render_template('suggest_idea.html')

@app.route('/suggestion/<int:suggestion_id>/update', methods=['POST'])
def update_suggestion(suggestion_id):
    if 'user_id' not in session or session.get('user_id') != 1:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    status = request.form.get('status')
    
    if status not in ['approved', 'rejected', 'pending', 'implemented']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    conn = get_db_connection()
    
    # Delete rejected suggestions
    if status == 'rejected':
        conn.execute("DELETE FROM suggestions WHERE id=?", (suggestion_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Suggestion rejected and deleted'})
    
    # Update status for others
    conn.execute("UPDATE suggestions SET status=? WHERE id=?", (status, suggestion_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Suggestion {status}'})

# -----------------------
# Profile
# -----------------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # Get user
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    # Update profile
    if request.method == "POST":
        bio = request.form.get("bio", "")
        interests = request.form.get("interests", "")
        avatar = user["avatar"]
        username = user["username"]  # Keep existing username by default
        badge = user["badge"] if user["badge"] else "none"

        # Allow premium users to change username and badge
        new_username = request.form.get("username", "").strip()
        new_badge = request.form.get("badge", "none")
        is_private = request.form.get("is_private") == "on"
        allow_messages = request.form.get("allow_messages") == "on"
        hide_followers = request.form.get("hide_followers") == "on"
        
        if user["subscription"] == "premium":
            # Allow username change
            if new_username and new_username != user["username"]:
                existing = conn.execute(
                    "SELECT id FROM users WHERE username=? AND id!=?",
                    (new_username, session["user_id"])
                ).fetchone()
                if not existing:
                    username = new_username
            
            # Allow badge change
            allowed_badges = ["none", "vip_pink", "vip_gold", "vip_blue", "vip_purple", "vip_green"]
            if new_badge in allowed_badges:
                badge = new_badge

        file = request.files.get("avatar")
        if file and file.filename and allowed_file(file.filename):
            avatar = storage.upload_avatar(file)

        conn.execute("""
            UPDATE users
            SET bio=?, avatar=?, username=?, badge=?, is_private=?, allow_messages=?, hide_followers=?, interests=?
            WHERE id=?
        """, (bio, avatar, username, badge, int(is_private), int(allow_messages), int(hide_followers), interests, session["user_id"]))

        conn.commit()
        conn.close()
        return redirect("/profile")

    # Load user's profile posts
    posts = conn.execute("""
        SELECT profile_posts.*, users.username, users.avatar, users.subscription AS user_subscription, users.badge AS user_badge
        FROM profile_posts
        JOIN users ON profile_posts.user_id = users.id
        WHERE profile_posts.user_id=?
        ORDER BY profile_posts.created_at DESC
    """, (session["user_id"],)).fetchall()

    # Load user's album images
    album_images = conn.execute("""
        SELECT * FROM album_images WHERE user_id=? ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    # Load user's products
    products = conn.execute("""
        SELECT * FROM products WHERE user_id=? ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    # Load user's stories for profile story viewer
    stories = conn.execute("""
        SELECT id, image, created_at
        FROM stories
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    stories_list = [dict(s) for s in stories]

    # Get follower counts
    follower_count = conn.execute(
        "SELECT COUNT(*) as count FROM followers WHERE following_id=?",
        (session["user_id"],)
    ).fetchone()["count"]
    
    following_count = conn.execute(
        "SELECT COUNT(*) as count FROM followers WHERE follower_id=?",
        (session["user_id"],)
    ).fetchone()["count"]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        album_images=album_images,
        products=products,
        stories=stories_list,
        follower_count=follower_count,
        following_count=following_count
    )


# -----------------------
# Photos Gallery
# -----------------------
@app.route("/photos")
def photos():
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db_connection()
    
    # Get user
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    
    # Get all photos from profile posts
    post_photos = conn.execute("""
        SELECT id, image, content AS caption, created_at, 
               strftime('%Y-%m-%d', created_at) AS date
        FROM profile_posts
        WHERE user_id=? AND image IS NOT NULL AND image != ''
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    
    # Get all photos from forum posts
    forum_photos = conn.execute("""
        SELECT id, image, content AS caption, created_at,
               strftime('%Y-%m-%d', created_at) AS date
        FROM posts
        WHERE user_id=? AND image IS NOT NULL AND image != ''
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    
    # Get all photos from album
    album_photos = conn.execute("""
        SELECT id, image, caption, created_at,
               strftime('%Y-%m-%d', created_at) AS date
        FROM album_images
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    
    conn.close()
    
    # Combine all photos with type indicator
    all_photos = []
    
    for photo in post_photos:
        all_photos.append({
            'id': photo['id'],
            'image': photo['image'],
            'caption': photo['caption'] or '',
            'content': photo['caption'] or '',
            'date': photo['date'],
            'type': 'post',
            'timestamp': photo['created_at']
        })
    
    for photo in forum_photos:
        all_photos.append({
            'id': photo['id'],
            'image': photo['image'],
            'caption': photo['caption'] or '',
            'content': photo['caption'] or '',
            'date': photo['date'],
            'type': 'forum_post',
            'timestamp': photo['created_at']
        })
    
    for photo in album_photos:
        all_photos.append({
            'id': photo['id'],
            'image': photo['image'],
            'caption': photo['caption'] or '',
            'content': '',
            'date': photo['date'],
            'type': 'album',
            'timestamp': photo['created_at']
        })
    
    # Sort by timestamp (newest first)
    all_photos.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template("photos.html", user=user, all_photos=all_photos)


# -----------------------
# Profile post (text + image + music)
# -----------------------

@app.route("/profile/post", methods=["POST"])
def add_profile_post():
    if "user_id" not in session:
        return redirect("/login")

    content = request.form.get("content","").strip()
    image   = request.files.get("image")
    music   = request.files.get("music")

    image_name = None
    music_name = None
    music_title = None

    if image and image.filename and allowed_file(image.filename):
        image_name = storage.upload_post_image(image)

    if music and music.filename and allowed_file(music.filename):
        # Store the original filename (with extension)
        music_title = music.filename
        music_name = storage.upload_music_file(music)

    if content or image_name or music_name:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO profile_posts (user_id,content,image,music,music_title)
            VALUES (?,?,?,?,?)
        """,(session["user_id"],content,image_name,music_name,music_title))
        conn.commit()
        conn.close()

    return redirect("/profile")



# -----------------------
# Likes & Comments
# -----------------------
@app.route("/like/<int:post_id>")
def like_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO likes (post_id,user_id) VALUES (?,?)",
                     (post_id, session["user_id"]))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect("/forum")

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    content = request.form.get("content", "").strip()

    if not content:
        return redirect("/forum")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO comments (post_id, user_id, content)
        VALUES (?, ?, ?)
    """, (post_id, session["user_id"], content))

    conn.commit()
    conn.close()

    return redirect("/forum")


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # Get comment to find the post_id and verify ownership
    comment = conn.execute(
        "SELECT post_id, user_id FROM comments WHERE id=?",
        (comment_id,)
    ).fetchone()

    if not comment:
        conn.close()
        return redirect("/forum")

    # Only delete your own comments
    if comment["user_id"] != session["user_id"]:
        conn.close()
        return redirect("/forum")

    # Delete the comment
    conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    conn.commit()
    conn.close()

    return redirect("/forum")


@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    # Only delete your own posts
    conn.execute(
        "DELETE FROM posts WHERE id=? AND user_id=?",
        (post_id, session['user_id'])
    )

    conn.commit()
    conn.close()

    # Redirect to photos if coming from there, otherwise forum
    referer = request.headers.get('Referer', '')
    if '/photos' in referer:
        return redirect('/photos')
    return redirect('/forum')

# -----------------------
# Friends System (FIXED)
# -----------------------

@app.route("/friends")
def friends():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # accepted friends
    friends = conn.execute("""
        SELECT u.* FROM users u
        JOIN friendships f 
          ON ((f.user_id = ? AND f.friend_id = u.id) 
           OR (f.friend_id = ? AND f.user_id = u.id))
        WHERE f.status = 'accepted'
          AND u.id != ?
    """, (session["user_id"], session["user_id"], session["user_id"])).fetchall()

    # pending requests
    pending_requests = conn.execute("""
        SELECT f.id,
               u.id AS user_id,
               u.username,
               u.avatar,
               u.subscription
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = ?
          AND f.status = 'pending'
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "friends.html",
        friends=friends,
        pending_requests=pending_requests
    )

@app.route("/followers")
def followers_page():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    
    # Get followers (users following me)
    followers = conn.execute("""
        SELECT u.*, 
               EXISTS(SELECT 1 FROM followers WHERE follower_id=? AND following_id=u.id) as is_following_back
        FROM users u
        JOIN followers f ON f.follower_id = u.id
        WHERE f.following_id = ?
    """, (session["user_id"], session["user_id"])).fetchall()
    
    # Get following (users I'm following)
    following = conn.execute("""
        SELECT u.*
        FROM users u
        JOIN followers f ON f.following_id = u.id
        WHERE f.follower_id = ?
    """, (session["user_id"],)).fetchall()
    
    conn.close()
    
    return render_template(
        "followers.html",
        followers=followers,
        following=following
    )

@app.route("/friend/requests")
def friend_requests():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    requests = conn.execute("""
        SELECT f.id AS request_id,
               u.id AS user_id,
               u.username,
               u.avatar,
               u.subscription
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = ? AND f.status = 'pending'
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("friend_requests.html", requests=requests)


@app.route("/friend/request/<int:user_id>")
def send_friend_request(user_id):
    if "user_id" not in session:
        return redirect("/login")

    if user_id == session["user_id"]:
        return redirect(f"/profile/{user_id}")

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (?, ?, 'pending')",
            (session["user_id"], user_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

    return redirect(f"/profile/{user_id}")

    

@app.route("/friend/accept/<int:req_id>")
def accept_friend(req_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute("UPDATE friendships SET status='accepted' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    return redirect("/friend/requests")


@app.route("/friend/reject/<int:req_id>")
def reject_friend(req_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute("DELETE FROM friendships WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    return redirect("/friend/requests")




@app.route("/friend/remove/<int:user_id>")
def remove_friend(user_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM friendships
        WHERE (user_id=? AND friend_id=?)
           OR (user_id=? AND friend_id=?)
    """, (
        session["user_id"], user_id,
        user_id, session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect("/friends")

# -----------------------
# Followers (Premium Only)
# -----------------------
@app.route("/follow/<int:user_id>", methods=["POST"])
def follow_user(user_id):
    if "user_id" not in session:
        return redirect("/login")

    if user_id == session["user_id"]:
        return redirect("/profile")

    conn = get_db_connection()
    
    # Check if current user is Premium
    current_user = conn.execute("SELECT subscription FROM users WHERE id=?", (session["user_id"],)).fetchone()
    # Check if target user is Premium
    target_user = conn.execute("SELECT subscription FROM users WHERE id=?", (user_id,)).fetchone()
    
    if current_user and current_user["subscription"] in ["basic", "pro", "premium"] and target_user and target_user["subscription"] in ["basic", "pro", "premium"]:
        try:
            conn.execute(
                "INSERT INTO followers (follower_id, following_id) VALUES (?, ?)",
                (session["user_id"], user_id)
            )
            conn.commit()
            flash('✓ You are now following this user!', 'success')
        except sqlite3.IntegrityError:
            flash('You are already following this user.', 'info')
    
    conn.close()
    # Redirect back to the user's profile
    return redirect(f"/profile/{user_id}")


@app.route("/unfollow/<int:user_id>", methods=["POST"])
def unfollow_user(user_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    result = conn.execute(
        "DELETE FROM followers WHERE follower_id=? AND following_id=?",
        (session["user_id"], user_id)
    )
    conn.commit()
    conn.close()
    
    flash('You have unfollowed this user.', 'info')
    return redirect(f"/profile/{user_id}")

@app.route("/block/<int:user_id>", methods=["POST"])
def block_user(user_id):
    if "user_id" not in session:
        return redirect("/login")

    if user_id == session["user_id"]:
        return redirect("/dashboard")

    conn = get_db_connection()
    
    try:
        # Add to blocked users
        conn.execute(
            "INSERT INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)",
            (session["user_id"], user_id)
        )
        
        # Remove any follower relationships
        conn.execute(
            "DELETE FROM followers WHERE (follower_id=? AND following_id=?) OR (follower_id=? AND following_id=?)",
            (session["user_id"], user_id, user_id, session["user_id"])
        )
        
        # Remove any friend relationships
        conn.execute(
            "DELETE FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
            (session["user_id"], user_id, user_id, session["user_id"])
        )
        
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    
    conn.close()
    
    # Redirect to referer or dashboard
    referer = request.headers.get('Referer', '')
    if '/followers' in referer:
        return redirect("/followers")
    elif '/profile' in referer:
        return redirect("/dashboard")
    return redirect("/dashboard")


@app.route("/unblock/<int:user_id>", methods=["POST"])
def unblock_user(user_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM blocked_users WHERE user_id=? AND blocked_user_id=?",
        (session["user_id"], user_id)
    )
    conn.commit()
    conn.close()
    
    return redirect("/dashboard")

# -----------------------
# Public profile
#------------------------
@app.route("/profile/<int:user_id>")
def view_user_profile(user_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:
        conn.close()
        return "User not found", 404

    # Check if profile is private and if current user can view it
    is_private = user["is_private"]
    current_user_id = session["user_id"]
    is_profile_owner = current_user_id == user_id
    
    # Check if users are friends
    is_friends = False
    if not is_profile_owner:
        friendship = conn.execute("""
            SELECT * FROM friendships
            WHERE (user_id=? AND friend_id=?)
               OR (user_id=? AND friend_id=?)
        """, (
            current_user_id, user_id,
            user_id, current_user_id
        )).fetchone()
        is_friends = friendship is not None
    
    # If profile is private and not owner/friend, show restricted message
    if is_private and not is_profile_owner and not is_friends:
        conn.close()
        return render_template("public_profile.html", user=user, is_restricted=True)

    profile_posts = conn.execute("""
        SELECT profile_posts.*, users.username, users.avatar, users.subscription AS user_subscription, users.badge AS user_badge
        FROM profile_posts
        JOIN users ON profile_posts.user_id = users.id
        WHERE profile_posts.user_id=?
        ORDER BY profile_posts.created_at DESC
    """, (user_id,)).fetchall()

    forum_posts = conn.execute("""
        SELECT posts.*, users.username, users.avatar, users.subscription AS user_subscription, users.badge AS user_badge
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.user_id=?
        ORDER BY posts.created_at DESC
    """, (user_id,)).fetchall()

    # Get user's stories
    user_stories = conn.execute("""
        SELECT * FROM stories 
        WHERE user_id=? 
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    products = conn.execute("""
        SELECT * FROM products WHERE user_id=? ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    friendship = conn.execute("""
        SELECT * FROM friendships
        WHERE (user_id=? AND friend_id=?)
           OR (user_id=? AND friend_id=?)
    """, (
        session["user_id"], user_id,
        user_id, session["user_id"]
    )).fetchone()

    # Get follower counts
    follower_count = conn.execute(
        "SELECT COUNT(*) as count FROM followers WHERE following_id=?",
        (user_id,)
    ).fetchone()["count"]
    
    following_count = conn.execute(
        "SELECT COUNT(*) as count FROM followers WHERE follower_id=?",
        (user_id,)
    ).fetchone()["count"]
    
    # Check if current user is following this user
    is_following = False
    if not is_profile_owner:
        is_following = conn.execute(
            "SELECT * FROM followers WHERE follower_id=? AND following_id=?",
            (current_user_id, user_id)
        ).fetchone() is not None

    conn.close()

    return render_template(
        "public_profile.html",
        user=user,
        profile_posts=profile_posts,
        forum_posts=forum_posts,
        user_stories=user_stories,
        products=products,
        friendship=friendship,
        is_restricted=False,
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following
    )

# -----------------------
# Messages
# -----------------------

@app.route("/messages")
def messages():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_subscription = get_subscription(conn, session.get("user_id"))
    is_basic = user_subscription in ("basic", "pro", "premium")
    is_premium = user_subscription == "premium"

    friends = conn.execute("""
        SELECT DISTINCT u.id, u.username, u.avatar, u.subscription, u.badge
        FROM users u
        JOIN messages m
            ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE u.id != ?
            AND (m.sender_id = ? OR m.receiver_id = ?)
        ORDER BY u.username
    """, (session["user_id"], session["user_id"], session["user_id"])).fetchall()

    stickers = conn.execute(
        "SELECT id, name, images FROM products WHERE type='sticker' ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "messages.html",
        friends=friends,
        messages=[],
        active_user=None,
        stickers=stickers,
        purchased_stickers=session.get('cart', []),
        is_basic=is_basic,
        is_premium=is_premium
    )


@app.route("/messages/<int:user_id>")
def open_chat(user_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_subscription = get_subscription(conn, session.get("user_id"))
    is_basic = user_subscription in ("basic", "pro", "premium")
    is_premium = user_subscription == "premium"
    is_pro = user_subscription in ("pro", "premium")

    friends = conn.execute("""
        SELECT DISTINCT u.id, u.username, u.avatar, u.subscription, u.badge
        FROM users u
        JOIN messages m
            ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE u.id != ?
            AND (m.sender_id = ? OR m.receiver_id = ?)
        ORDER BY u.username
    """, (session["user_id"], session["user_id"], session["user_id"])).fetchall()

    active_user = conn.execute("""
        SELECT id, username, avatar, subscription, badge, allow_messages
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    # Check if active user allows messages
    allow_messaging = True
    if active_user and not active_user["allow_messages"]:
        allow_messaging = False

    messages = conn.execute("""
        SELECT m.*, u.avatar
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id=? AND m.receiver_id=?)
           OR (m.sender_id=? AND m.receiver_id=?)
        ORDER BY m.created_at ASC
    """, (
        session["user_id"], user_id,
        user_id, session["user_id"]
    )).fetchall()
    
    # Mark messages as read when user opens the chat
    conn.execute("""
        UPDATE messages SET is_read=1 
        WHERE receiver_id=? AND sender_id=? AND is_read=0
    """, (session["user_id"], user_id))
    conn.commit()

    stickers = conn.execute(
        "SELECT id, name, images FROM products WHERE type='sticker' ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template("messages.html",
                           friends=friends,
                           messages=messages,
                           active_user=active_user,
                           stickers=stickers,
                           purchased_stickers=session.get('cart', []),
                           is_basic=is_basic,
                           is_pro=is_pro,
                           is_premium=is_premium,
                           allow_messaging=allow_messaging)

@app.route("/upload_message_file", methods=["POST"])
def upload_message_file():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    file = request.files.get("file")
    file_type = request.form.get("type")  # "image" or "music"
    
    if not file or not file.filename or not allowed_file(file.filename):
        return {"error": "Invalid file"}, 400
    
    if file_type == "music":
        filepath = storage.upload_music_file(file)
    else:  # image
        filepath = storage.upload_post_image(file)
    
    if not filepath:
        return {"error": "Upload failed"}, 500
    
    return {"success": True, "filepath": filepath, "filename": file.filename}

# @socketio.on('join')  # Disabled for deployment
# def handle_join(data):
#     join_room(data['room'])


# @socketio.on('send_message')  # Disabled for deployment
# def handle_send_message(data):
#     try:
#         sender   = data.get('sender')
#         receiver = data.get('receiver')
#         content  = data.get('content')
#         sticker  = data.get('sticker')
#         money_amount = data.get('money_amount')
#         image    = data.get('image')
#         music    = data.get('music')
#         music_title = data.get('music_title')
# 
#         if not sender or not receiver:
#             emit('error', {'message': 'Invalid sender or receiver'})
#             return
# 
#         conn = get_db_connection()
#         
#         # Check if receiver allows messages
#         receiver_user = conn.execute(
#             "SELECT allow_messages FROM users WHERE id=?",
#             (receiver,)
#         ).fetchone()
#         
#         if receiver_user and not receiver_user['allow_messages']:
#             conn.close()
#             emit('message_blocked', {'error': 'This user has disabled direct messages'})
#             return
#         
#         # If sending money, verify balance and process transfer
#         if money_amount and float(money_amount) > 0:
#             sender_user = conn.execute(
#                 "SELECT wallet_balance, subscription FROM users WHERE id=?",
#                 (sender,)
#             ).fetchone()
#             
#             # Check if user has Pro or Premium subscription
#             if sender_user['subscription'] not in ('pro', 'premium'):
#                 conn.close()
#                 return
#             
#             amount = float(money_amount)
#             if sender_user['wallet_balance'] < amount:
#                 conn.close()
#                 return
#             
#             # Deduct from sender
#             conn.execute(
#                 "UPDATE users SET wallet_balance = wallet_balance - ? WHERE id=?",
#                 (amount, sender)
#             )
#             
#             # Add to receiver
#             conn.execute(
#                 "UPDATE users SET wallet_balance = wallet_balance + ? WHERE id=?",
#                 (amount, receiver)
#             )
#             
#             # Record transactions
#             conn.execute(
#                 "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'transfer_out', ?, ?)",
#                 (sender, -amount, f"Sent to user #{receiver}")
#             )
#             conn.execute(
#                 "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'transfer_in', ?, ?)",
#                 (receiver, amount, f"Received from user #{sender}")
#             )
#         
#         cur = conn.execute("""
#             INSERT INTO messages (sender_id, receiver_id, content, sticker, money_amount, image, music, music_title)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (sender, receiver, content, sticker, money_amount, image, music, music_title))
#         conn.commit()
#         msg_id = cur.lastrowid
#         conn.close()
# 
#         room = f"chat_{min(sender,receiver)}_{max(sender,receiver)}"
# 
#         emit("receive_message", {
#             "id": msg_id,
#             "sender": sender,
#             "content": content,
#             "sticker": sticker,
#             "money_amount": money_amount,
#             "image": image,
#             "music": music,
#             "music_title": music_title
#         }, room=room)
#     except Exception as e:
#         import traceback
#         print(f"Error in handle_send_message: {e}")
#         traceback.print_exc()
#         emit('error', {'message': str(e)})


# -----------------------
# Watch Together WebSocket Events
# -----------------------
# @socketio.on('join_watch_room')  # Disabled for deployment
# def handle_join_watch_room(data):
#     room_id = data.get('room_id')
#     user_id = data.get('user_id')
#     username = data.get('username')
#     
#     if not room_id:
#         return
#     
#     room = f"watch_{room_id}"
#     join_room(room)
#     
#     # Notify others that user joined
#     emit('user_joined', {
#         'user_id': user_id,
#         'username': username,
#         'message': f'{username} joined the watch party'
#     }, room=room, include_self=False)


# @socketio.on('video_play')  # Disabled for deployment
# def handle_video_play(data):
#     room_id = data.get('room_id')
#     current_time = data.get('current_time', 0)
#     
#     if not room_id:
#         return
#     
#     # Update database
#     conn = get_db_connection()
#     conn.execute("""
#         UPDATE watch_rooms SET is_playing=1, current_time=? WHERE id=?
#     """, (current_time, room_id))
#     conn.commit()
#     conn.close()
#     
#     room = f"watch_{room_id}"
#     emit('sync_play', {'current_time': current_time}, room=room, include_self=False)


# @socketio.on('video_pause')  # Disabled for deployment
# def handle_video_pause(data):
#     room_id = data.get('room_id')
#     current_time = data.get('current_time', 0)
#     
#     if not room_id:
#         return
#     
#     # Update database
#     conn = get_db_connection()
#     conn.execute("""
#         UPDATE watch_rooms SET is_playing=0, current_time=? WHERE id=?
#     """, (current_time, room_id))
#     conn.commit()
#     conn.close()
#     
#     room = f"watch_{room_id}"
#     emit('sync_pause', {'current_time': current_time}, room=room, include_self=False)


# @socketio.on('video_seek')  # Disabled for deployment
# def handle_video_seek(data):
#     room_id = data.get('room_id')
#     current_time = data.get('current_time', 0)
#     
#     if not room_id:
#         return
#     
#     # Update database
#     conn = get_db_connection()
#     conn.execute("""
#         UPDATE watch_rooms SET current_time=? WHERE id=?
#     """, (current_time, room_id))
#     conn.commit()
#     conn.close()
#     
#     room = f"watch_{room_id}"
#     emit('sync_seek', {'current_time': current_time}, room=room, include_self=False)


# @socketio.on('watch_chat_message')  # Disabled for deployment
# def handle_watch_chat(data):
#     room_id = data.get('room_id')
#     username = data.get('username')
#     message = data.get('message', '').strip()
#     
#     if not room_id or not message:
#         return
#     
#     room = f"watch_{room_id}"
#     emit('watch_chat_receive', {
#         'username': username,
#         'message': message
#     }, room=room)


@app.route('/messages/edit/<int:msg_id>', methods=['POST'])
def edit_message(msg_id):
    if 'user_id' not in session:
        return jsonify({"error": "auth"}), 401
    
    data = request.get_json()
    new_content = data.get('content', '').strip()
    
    if not new_content:
        return jsonify({"error": "empty content"}), 400
    
    conn = get_db_connection()
    
    # Verify user owns this message
    msg = conn.execute(
        "SELECT sender_id FROM messages WHERE id=?",
        (msg_id,)
    ).fetchone()
    
    if not msg or msg['sender_id'] != session['user_id']:
        conn.close()
        return jsonify({"error": "unauthorized"}), 403
    
    # Update message
    conn.execute(
        "UPDATE messages SET content=? WHERE id=?",
        (new_content, msg_id)
    )
    conn.commit()
    conn.close()
    
    # Notify via Socket.IO
    # socketio.emit("message_edited", {  # Disabled for deployment
    #     "id": msg_id,
    #     "content": new_content
    # }, broadcast=True)
    
    return jsonify({"success": True})


@app.route('/messages/delete/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if 'user_id' not in session:
        return jsonify({"error": "auth"}), 401
    
    conn = get_db_connection()
    
    # Verify user owns this message
    msg = conn.execute(
        "SELECT sender_id FROM messages WHERE id=?",
        (msg_id,)
    ).fetchone()
    
    if not msg or msg['sender_id'] != session['user_id']:
        conn.close()
        return jsonify({"error": "unauthorized"}), 403
    
    # Delete message
    conn.execute(
        "DELETE FROM messages WHERE id=?",
        (msg_id,)
    )
    conn.commit()
    conn.close()
    
    # Notify via Socket.IO
    # socketio.emit("message_deleted", {  # Disabled for deployment
    #     "id": msg_id
    # }, broadcast=True)
    
    return jsonify({"success": True})

@app.route('/subscription/cancel', methods=['POST'])
def cancel_subscription():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET subscription='none' WHERE id=?",
        (session['user_id'],)
    )
    
    conn.execute(
        "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'subscription_cancel', ?, ?)",
        (session['user_id'], 0, "Subscription cancelled")
    )
    
    conn.commit()
    conn.close()
    
    return redirect('/subscription?success=1')

# -----------------------
# Watch Together
# -----------------------
@app.route('/watch')
def watch_together():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    # Get all active watch rooms - public rooms visible to all, private rooms only to host/participants
    rooms = conn.execute("""
        SELECT wr.*, u.username as host_name, u.avatar as host_avatar,
               (SELECT COUNT(*) FROM watch_participants WHERE room_id=wr.id) as participant_count
        FROM watch_rooms wr
        JOIN users u ON wr.host_id = u.id
        WHERE wr.is_active = 1 AND (
            wr.is_private = 0 OR 
            wr.host_id = ? OR 
            wr.id IN (SELECT room_id FROM watch_participants WHERE user_id = ?)
        )
        ORDER BY wr.created_at DESC
    """, (session['user_id'], session['user_id'])).fetchall()
    
    conn.close()
    
    return render_template('watch_together.html', user=user, rooms=rooms)

@app.route('/watch/create', methods=['POST'])
def create_watch_room():
    if 'user_id' not in session:
        return redirect('/login')
    
    youtube_url = request.form.get('youtube_url', '').strip()
    room_name = request.form.get('room_name', 'Watch Room').strip()
    is_private = int(request.form.get('is_private', '0'))
    
    if not youtube_url:
        return redirect('/watch?error=no_url')
    
    # Extract video ID from YouTube URL
    video_id = None
    if 'youtube.com/watch?v=' in youtube_url:
        video_id = youtube_url.split('watch?v=')[1].split('&')[0]
    elif 'youtu.be/' in youtube_url:
        video_id = youtube_url.split('youtu.be/')[1].split('?')[0]
    
    if not video_id:
        return redirect('/watch?error=invalid_url')
    
    conn = get_db_connection()
    cursor = conn.execute("""
        INSERT INTO watch_rooms (host_id, room_name, video_id, current_time, is_playing, is_active, is_private)
        VALUES (?, ?, ?, 0, 0, 1, ?)
    """, (session['user_id'], room_name, video_id, is_private))
    room_id = cursor.lastrowid
    
    # Add host as participant
    conn.execute("""
        INSERT INTO watch_participants (room_id, user_id)
        VALUES (?, ?)
    """, (room_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    return redirect(f'/watch/room/{room_id}')

@app.route('/watch/room/<int:room_id>')
def watch_room(room_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    
    room = conn.execute("""
        SELECT wr.*, u.username as host_name, u.avatar as host_avatar
        FROM watch_rooms wr
        JOIN users u ON wr.host_id = u.id
        WHERE wr.id = ?
    """, (room_id,)).fetchone()
    
    if not room or not room['is_active']:
        conn.close()
        return redirect('/watch?error=room_not_found')
    
    # Add user as participant if not already
    existing = conn.execute("""
        SELECT * FROM watch_participants WHERE room_id=? AND user_id=?
    """, (room_id, session['user_id'])).fetchone()
    
    if not existing:
        conn.execute("""
            INSERT INTO watch_participants (room_id, user_id)
            VALUES (?, ?)
        """, (room_id, session['user_id']))
        conn.commit()
    
    # Get all participants
    participants = conn.execute("""
        SELECT u.id, u.username, u.avatar
        FROM watch_participants wp
        JOIN users u ON wp.user_id = u.id
        WHERE wp.room_id = ?
        ORDER BY wp.joined_at ASC
    """, (room_id,)).fetchall()
    
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    conn.close()
    
    return render_template('watch_room.html', room=room, participants=participants, user=user)

@app.route('/watch/leave/<int:room_id>', methods=['POST'])
def leave_watch_room(room_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    
    # Remove participant
    conn.execute("""
        DELETE FROM watch_participants WHERE room_id=? AND user_id=?
    """, (room_id, session['user_id']))
    
    # Check if host is leaving
    room = conn.execute("SELECT * FROM watch_rooms WHERE id=?", (room_id,)).fetchone()
    if room and room['host_id'] == session['user_id']:
        # Deactivate room if host leaves
        conn.execute("UPDATE watch_rooms SET is_active=0 WHERE id=?", (room_id,))
    
    conn.commit()
    conn.close()
    
    return redirect('/watch')

@app.route('/watch/delete/<int:room_id>', methods=['POST'])
def delete_watch_room(room_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    # Only admin can delete rooms
    if session.get('user_id') != 1:
        flash('Only admin can delete rooms', 'error')
        return redirect('/watch')
    
    conn = get_db_connection()
    
    # Delete all participants first
    conn.execute("DELETE FROM watch_participants WHERE room_id=?", (room_id,))
    
    # Delete the room
    conn.execute("DELETE FROM watch_rooms WHERE id=?", (room_id,))
    
    conn.commit()
    conn.close()
    
    flash('Room deleted successfully', 'success')
    return redirect('/watch')

@app.route('/purchases')
def purchases():
    if 'user_id' not in session:
        return redirect('/login')
    # Admin only
    if session.get('user_id') != 1:
        return redirect('/forum')
    
    conn = get_db_connection()
    
    # Get all purchased products
    purchased_products = conn.execute("""
        SELECT 
            products.*, 
            users.username as seller_username,
            purchases.purchased_at
        FROM purchases
        JOIN products ON purchases.product_id = products.id
        JOIN users ON products.user_id = users.id
        WHERE purchases.user_id = ?
        ORDER BY purchases.purchased_at DESC
    """, (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('purchases.html', products=purchased_products)

@app.route('/admin/users', methods=['GET','POST'])
def admin_users():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('email') != ADMIN_EMAIL:
        return redirect('/dashboard')

    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_subscription':
            user_id = request.form.get('user_id')
            subscription = request.form.get('subscription') or 'none'
            if subscription not in ('none','basic','pro','premium'):
                subscription = 'none'
            conn.execute(
                "UPDATE users SET subscription=? WHERE id=?",
                (subscription, user_id)
            )
            conn.commit()
        
        elif action == 'send_money':
            user_id = request.form.get('user_id')
            amount = request.form.get('amount')
            try:
                amount = float(amount)
                if amount > 0:
                    conn.execute(
                        "UPDATE users SET wallet_balance = wallet_balance + ? WHERE id=?",
                        (amount, user_id)
                    )
                    conn.execute(
                        "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'admin_credit', ?, ?)",
                        (user_id, amount, "Admin credit")
                    )
                    conn.commit()
            except ValueError:
                pass

    users = conn.execute(
        "SELECT id, username, email, subscription, wallet_balance FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)


# -----------------------
# Watch Together APIs
# -----------------------
@app.route('/api/friends')
def api_get_friends():
    """Get current user's friends list"""
    if 'user_id' not in session:
        return jsonify([]), 401
    
    conn = get_db_connection()
    friends = conn.execute("""
        SELECT DISTINCT u.id, u.username FROM users u
        JOIN friendships f ON (
            (f.user_id = ? AND f.friend_id = u.id) OR
            (f.friend_id = ? AND f.user_id = u.id)
        )
        WHERE f.status = 'accepted'
        ORDER BY u.username
    """, (session['user_id'], session['user_id'])).fetchall()
    conn.close()
    
    return jsonify({
        'friends': [dict(f) for f in friends]
    })

@app.route('/api/search-users')
def api_search_users():
    """Search for users"""
    if 'user_id' not in session:
        return jsonify([]), 401
    
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'users': []})
    
    conn = get_db_connection()
    users = conn.execute("""
        SELECT u.id, u.username, 
               CASE 
                   WHEN EXISTS (SELECT 1 FROM friendships WHERE 
                       ((user_id=? AND friend_id=u.id) OR (friend_id=? AND user_id=u.id)))
                   THEN CASE 
                       WHEN EXISTS (SELECT 1 FROM friendships WHERE 
                           ((user_id=? AND friend_id=u.id) OR (friend_id=? AND user_id=u.id)) 
                           AND status='accepted')
                       THEN 'accepted'
                       ELSE 'pending'
                   END
                   ELSE 'none'
               END as friendship_status
        FROM users u
        WHERE u.id != ? AND LOWER(u.username) LIKE LOWER(?)
        LIMIT 10
    """, (session['user_id'], session['user_id'], session['user_id'], 
          session['user_id'], session['user_id'], f'%{query}%')).fetchall()
    conn.close()
    
    return jsonify({
        'users': [dict(u) for u in users]
    })

@app.route('/api/send-room-invite/<int:friend_id>', methods=['POST'])
def api_send_room_invite(friend_id):
    """Send a room invite notification to a friend"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    room_link = data.get('room_link', '')
    
    return jsonify({
        'success': True,
        'message': f'Invitation sent to friend {friend_id}'
    })

@app.route('/api/user-online/<int:user_id>')
def api_check_user_online(user_id):
    """Check if a user is currently online"""
    return jsonify({
        'user_id': user_id,
        'online': is_user_online(user_id)
    })

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
