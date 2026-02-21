# 🎉 Fanvy - Social Platform

A modern social networking platform built with Flask, featuring real-time chat, stories, watch together, and more!

## ✨ Features

- 👤 **User Profiles** - Customizable profiles with avatars and bio
- 💬 **Real-time Messaging** - WebSocket-based chat with online status
- 📸 **Stories** - Share photos that disappear after 24 hours
- 🎬 **Watch Together** - Synchronized video watching with friends
- 🏪 **Shop** - Subscription tiers (Basic, Premium, VIP)
- 👥 **Social Features** - Friends, followers, friend requests
- 📱 **Forum** - Community posts with interest-based feed
- 🔔 **Notifications** - Real-time badges for messages, friend requests
- 💡 **User Suggestions** - Let users suggest new features
- ⚙️ **Admin Dashboard** - User approval system, applications management
- 🎨 **Dark/Light Mode** - Theme toggle support

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project**:
   ```bash
   cd /Users/hk/learnsocial
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   python app.py
   # Or use the startup script:
   ./start.sh
   ```

5. **Open your browser**:
   ```
   http://localhost:5000
   ```

## 🌐 Deploy to Internet (FREE)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to:
- **Render** (Recommended)
- **PythonAnywhere**
- **Railway**

Quick deploy to Render:
```bash
git init
git add .
git commit -m "Initial commit"
# Push to GitHub, then connect to Render
```

## 📁 Project Structure

```
fanvy/
├── app.py                 # Main Flask application
├── storage.py             # File storage handler (Supabase/local)
├── email_service.py       # Email verification service
├── email_config.py        # Email configuration
├── users.db              # SQLite database
├── static/               # CSS, images, uploads
│   ├── style.css
│   ├── avatars/
│   ├── uploads/
│   ├── stories/
│   ├── music/
│   └── photos/
├── templates/            # HTML templates
│   ├── forum.html
│   ├── messages.html
│   ├── profile.html
│   └── ...
├── requirements.txt      # Python dependencies
└── DEPLOYMENT.md         # Deployment guide
```

## 🔧 Configuration

### Email Setup (Optional)

Edit `email_config.py`:
```python
EMAIL_ENABLED = True
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"  # Gmail App Password
```

### Supabase Storage (Optional)

Edit `storage.py` with your Supabase credentials for cloud file storage.

### Admin Account

First user (ID=1) is automatically admin with access to:
- User approval dashboard
- Applications management
- Feature suggestions review
- Shop management

## 🎯 Key Routes

- `/register` - User registration
- `/login` - User login
- `/forum` - Main feed
- `/messages` - Direct messaging
- `/profile` - User profile
- `/friends` - Friends management
- `/watch` - Watch together rooms
- `/shop` - Subscription shop
- `/admin/pending-users` - Admin user approvals
- `/applications` - Admin applications & suggestions

## 🛠️ Tech Stack

- **Backend**: Flask 3.1.3
- **WebSocket**: Flask-SocketIO
- **Database**: SQLite (dev), PostgreSQL (production recommended)
- **Storage**: Supabase or local file system
- **Email**: SMTP (Gmail)
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Gunicorn + Eventlet

## 📝 License

This project is open source and available for personal use.

## 🤝 Contributing

Want to suggest a feature? Use the "Suggest an Idea" button in the app!

## 📧 Contact

Admin Email: ho.swag@mail.ru

---

**Made with ❤️ for the Fanvy community**
