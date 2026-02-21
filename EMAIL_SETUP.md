# 📧 Gmail Email Setup Guide

## How to Send Real Emails to Users

Your app is ready to send verification codes via Gmail SMTP! Follow these steps:

### Step 1: Get Your Gmail Account Ready

1. Go to **myaccount.google.com**
2. Click **Security** (left sidebar)
3. Scroll to **How you sign in to Google**
4. Enable **2-Step Verification** (if not already enabled)
5. Go back to **Security**
6. Find **App passwords** section
7. Select **Mail** and **Windows Computer**
8. Google will generate a 16-character password (e.g., `abcd efgh ijkl mnop`)

**IMPORTANT:** Copy this password - you'll only see it once!

---

### Step 2: Update Configuration

Edit [email_config.py](email_config.py):

```python
# Your Gmail address
EMAIL_ADDRESS = "your-email@gmail.com"

# The 16-character App Password (remove spaces)
EMAIL_PASSWORD = "abcdefghijklmnop"

# Enable email sending
EMAIL_ENABLED = True
```

**Example:**
```python
EMAIL_ADDRESS = "learnsocial@gmail.com"
EMAIL_PASSWORD = "abcdefghijklmnop"  # 16 chars, no spaces
EMAIL_ENABLED = True
```

---

### Step 3: (Optional) Update App URL

If deploying to production, update the email links:

```python
# For localhost (testing)
APP_URL = "http://localhost:5000"

# For production (example)
APP_URL = "https://yourdomain.com"
```

---

## How It Works

### When User Registers:

```
1. User fills form → /register
2. Account created with 6-digit code
3. Email SENT to user's inbox
4. User redirected to /verify
5. User checks email, enters code
6. Account verified! Can now login
```

### What User Receives:

✉️ **Professional HTML Email:**
- Verification code displayed clearly
- Nice formatting with app branding
- 15-minute expiration notice
- Login instructions

---

## Testing Without Gmail Setup

If you don't set up Gmail yet:

1. Leave `EMAIL_ENABLED = False` in email_config.py
2. Verification codes will show on screen instead of email
3. Users can still test registration/verification flow
4. Codes display in the UI temporarily

---

## Troubleshooting

### "Login password incorrect" error
- Make sure you're using the **App Password** (16 chars)
- NOT your regular Gmail password
- Remove any spaces from the App Password

### "The plain SMTP authentication is disabled" error
- Check that you enabled 2-Step Verification first
- App Passwords only work with 2FA enabled

### Email not sending silently
- Check app.py logs for errors
- Verify EMAIL_ENABLED = True
- Confirm credentials are correct

### Want to ensure emails will send?
Test it from Python:

```python
python3 -c "import email_service; email_service.send_verification_email('test@gmail.com', 'testuser', '123456')"
```

---

## Security Tips

🔒 **Never** commit actual credentials to git:

```bash
# Add to .gitignore
echo "email_config.py" >> .gitignore
```

If sharing code:
```python
# Use environment variables instead
import os
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
```

---

## After Setup

1. Save [email_config.py](email_config.py)
2. Restart your Flask app
3. Try registering a new user
4. Check your inbox!

**Expected behavior:**
- ✅ Registration successful
- ✅ Email arrives in ~seconds
- ✅ User can verify and login

---

## Email Features Included

✉️ **Verification Email:**
- 6-digit code
- HTML formatted
- Professional design

🎉 **Approval Notification** (if using admin approval):
- User notified when account approved
- Login link included

---

## What Happens If Email Fails?

If email_service can't send (no credentials):
- Verification code shows on screen
- Development/testing still works
- No email, but flow continues
- ⚠️ Shows error in terminal

This is intentional - you can test without real emails!

---

## Ready to Send Emails?

1. ✅ Enable 2FA on Google Account
2. ✅ Get App Password from Google
3. ✅ Update email_config.py
4. ✅ Restart Flask app
5. ✅ Test with new registration

That's it! 🚀
