# 🚀 Deploy Fanvy to PythonAnywhere (FREE)

Complete step-by-step guide to get Fanvy online for free!

---

## Step 1: Create PythonAnywhere Account

1. Go to: **https://www.pythonanywhere.com/registration/register/beginner/**
2. Fill in:
   - Username (this will be in your URL: `username.pythonanywhere.com`)
   - Email
   - Password
3. Click **"Register"**
4. Verify your email

✅ **No credit card needed!**

---

## Step 2: Upload Your Code from GitHub

### Option A: Clone from GitHub (Recommended)

1. Click **"Consoles"** tab
2. Click **"Bash"**
3. In the terminal, run:

```bash
git clone https://github.com/alynikitina204-cmyk/fanvy.git
cd fanvy
ls -la
```

✅ All your files are now uploaded!

### Option B: Manual Upload (if GitHub doesn't work)

1. Click **"Files"** tab
2. Create a folder: `fanvy`
3. Upload files one by one (app.py, storage.py, etc.)

---

## Step 3: Install Dependencies

1. In the **Bash console**, run:

```bash
cd fanvy
pip3.10 install --user flask flask-socketio eventlet werkzeug requests supabase
```

Wait 2-3 minutes for installation...

✅ Dependencies installed!

---

## Step 4: Create Web App

1. Click **"Web"** tab (top menu)
2. Click **"Add a new web app"**
3. Click **"Next"** (ignore the domain name for now)
4. Choose **"Manual configuration"**
5. Select **"Python 3.10"**
6. Click **"Next"** and **"Next"** again

✅ Web app created!

---

## Step 5: Configure WSGI File

1. In the **Web** tab, scroll to **"Code"** section
2. Click the **WSGI configuration file** link (e.g., `/var/www/username_pythonanywhere_com_wsgi.py`)
3. **Delete everything** in the file
4. Replace with this code:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/fanvy'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['SECRET_KEY'] = 'your-secret-key-change-this-123456789'

# Import Flask app
from app import app as application
```

5. **IMPORTANT**: Replace `YOUR_USERNAME` with your actual PythonAnywhere username
6. Click **"Save"** (top right)

---

## Step 6: Set Static Files

1. Still in the **Web** tab, scroll to **"Static files"** section
2. Click **"Enter URL"** and add:
   - URL: `/static/`
   - Directory: `/home/YOUR_USERNAME/fanvy/static/`
3. Replace `YOUR_USERNAME` with your username
4. Click the checkmark ✓

---

## Step 7: Upload Database

### Option A: Create Fresh Database

Skip this - PythonAnywhere will create a new `users.db` automatically when first user registers.

### Option B: Upload Your Existing Database

1. Click **"Files"** tab
2. Navigate to `/home/YOUR_USERNAME/fanvy/`
3. Click **"Upload a file"**
4. Upload your `users.db` from your Mac

---

## Step 8: Fix File Permissions

1. Go back to **Bash console**
2. Run:

```bash
cd /home/YOUR_USERNAME/fanvy
chmod 644 users.db
mkdir -p static/uploads static/avatars static/stories static/photos
chmod 755 static/uploads static/avatars static/stories static/photos
```

Replace `YOUR_USERNAME` with your username.

---

## Step 9: Reload Web App

1. Go to **Web** tab
2. Scroll to the top
3. Click the big green **"Reload"** button

Wait 30 seconds...

---

## Step 10: Visit Your Site! 🎉

Your Fanvy is now live at:

**`https://YOUR_USERNAME.pythonanywhere.com`**

Replace `YOUR_USERNAME` with your actual username!

---

## 🔧 Troubleshooting

### Problem: "Import Error" or "Module not found"

**Solution**: Re-install dependencies:
```bash
cd ~/fanvy
pip3.10 install --user flask flask-socketio eventlet werkzeug requests supabase
```
Then reload the web app.

### Problem: "Database is locked"

**Solution**: Fix permissions:
```bash
cd ~/fanvy
chmod 666 users.db
```

### Problem: Static files (CSS) not loading

**Solution**: Check static files path in Web tab:
- URL: `/static/`
- Directory: `/home/YOUR_USERNAME/fanvy/static/` ← Must match exactly!

### Problem: Can't upload files (avatars, photos)

**Solution**: PythonAnywhere free tier has limited disk space. Use Supabase storage instead (you already have this in your code!).

---

## 📝 Important Notes

### Database
- ✅ Your database persists (doesn't reset like Render)
- ✅ User accounts stay saved
- ⚠️ Limited to 512 MB storage on free tier

### File Uploads
- ⚠️ Limited disk space (512 MB total)
- 💡 **Solution**: Configure Supabase storage (already in your code!)

### WebSockets (Real-time Chat)
- ⚠️ WebSockets don't work on PythonAnywhere free tier
- Your chat will still work, but need to refresh to see new messages
- Upgrade to paid tier ($5/month) to enable WebSockets

### Performance
- ✅ No cold starts - always fast!
- ✅ Always online - doesn't sleep

---

## 🔄 Updating Your Site

When you make changes locally:

1. **Commit and push to GitHub**:
```bash
git add .
git commit -m "Updated feature"
git push origin main
```

2. **Pull on PythonAnywhere**:
- Go to Bash console
```bash
cd ~/fanvy
git pull origin main
```

3. **Reload web app**:
- Web tab → Click "Reload" button

---

## 🆙 Upgrade Options

**Free tier limitations**:
- 512 MB disk space
- No WebSocket support
- 1 web app only

**Upgrade to Hacker tier ($5/month)**:
- More disk space
- WebSocket support (real-time chat works!)
- Multiple web apps
- Custom domain support

---

## ✅ Checklist

- [ ] Created PythonAnywhere account
- [ ] Cloned code from GitHub
- [ ] Installed dependencies
- [ ] Created web app
- [ ] Configured WSGI file (with your username!)
- [ ] Set static files path
- [ ] Reloaded web app
- [ ] Visited site and it works!

---

## 🎯 Your URLs

- **Website**: `https://YOUR_USERNAME.pythonanywhere.com`
- **Admin Dashboard**: `https://YOUR_USERNAME.pythonanywhere.com/admin/pending-users`
- **GitHub Repo**: https://github.com/alynikitina204-cmyk/fanvy

---

## 🆘 Need Help?

If you get stuck on any step, let me know which step and what error message you see!

**Common issues**:
1. Wrong username in WSGI file
2. Wrong static files path
3. Forgot to reload web app
4. Dependencies not installed

---

**Good luck! Your Fanvy will be live in 10 minutes!** 🚀
