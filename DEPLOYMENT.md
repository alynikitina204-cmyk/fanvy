# Deploy Fanvy to the Internet (FREE) 🚀

Your app is now ready to deploy! Here are the **best free hosting options**:

---

## Option 1: **Render** (Recommended - Easiest) ⭐

### Steps:

1. **Create a GitHub account** (if you don't have one):
   - Go to https://github.com/signup

2. **Install Git** (if not installed):
   ```bash
   git --version  # Check if installed
   ```

3. **Initialize Git in your project**:
   ```bash
   cd /Users/hk/learnsocial
   git init
   git add .
   git commit -m "Initial commit - Fanvy social platform"
   ```

4. **Create a new repository on GitHub**:
   - Go to https://github.com/new
   - Name: `fanvy`
   - Make it **Public**
   - Don't add README, .gitignore, or license (we have them)
   - Click "Create repository"

5. **Push your code to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/fanvy.git
   git branch -M main
   git push -u origin main
   ```

6. **Deploy on Render**:
   - Go to https://render.com/
   - Sign up with GitHub
   - Click "New +" → "Web Service"
   - Connect your `fanvy` repository
   - Configure:
     - **Name**: fanvy
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
     - **Instance Type**: Free
   - Click "Create Web Service"

7. **Your app will be live at**: `https://fanvy.onrender.com` (or similar)

⚠️ **Note**: Free tier goes to sleep after 15 minutes of inactivity. First request takes ~30 seconds.

---

## Option 2: **PythonAnywhere** (Good for beginners)

### Steps:

1. **Sign up**: https://www.pythonanywhere.com/registration/register/beginner/
2. **Upload your code**: Use their file manager or git
3. **Create a web app**: Python 3.10, Flask
4. **Install dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
5. **Configure WSGI file** to point to your app
6. **Reload** and your site is live!

Free tier: `https://YOUR_USERNAME.pythonanywhere.com`

---

## Option 3: **Railway** (Very fast deployment)

### Steps:

1. Go to https://railway.app/
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `fanvy` repository
5. Railway auto-detects Python and deploys!
6. Add environment variable: `SECRET_KEY` = (random string)

Free tier: $5 credit/month (usually enough)

---

## Important Database Notes ⚠️

**SQLite doesn't work well on free hosting** because:
- File system is ephemeral (resets on restart)
- Data gets deleted

### Solutions:

1. **Use Render PostgreSQL** (Free):
   - When creating web service, also create PostgreSQL database
   - Update your code to use PostgreSQL instead of SQLite

2. **Use Supabase** (Free):
   - Go to https://supabase.com/
   - Create a free project
   - Get PostgreSQL connection string
   - Update your database connection

3. **For testing only**: Keep SQLite, but know data will reset

---

## Quick Start Commands:

```bash
# 1. Initialize git
cd /Users/hk/learnsocial
git init
git add .
git commit -m "Initial commit"

# 2. Create GitHub repo and push
# (Follow GitHub instructions after creating repo)

# 3. Deploy on Render (via web interface)
```

---

## Files Created for Deployment:

✅ `requirements.txt` - Python dependencies
✅ `.gitignore` - Files to exclude from git
✅ `Procfile` - How to run the app
✅ `render.yaml` - Render configuration
✅ `runtime.txt` - Python version

---

## Environment Variables to Set:

- `SECRET_KEY`: Random string for session security
- `PORT`: Auto-set by hosting platform

---

## Need Help?

Choose **Render** if you want:
- ✅ Easy deployment
- ✅ Free HTTPS
- ✅ Auto-deploys from GitHub
- ✅ PostgreSQL database included

Let me know which platform you want to use and I'll help with specific setup!
