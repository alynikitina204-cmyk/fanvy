# Email Configuration for Gmail SMTP
# Copy this file to email_config.py and update with your credentials

# Gmail SMTP Settings
EMAIL_ENABLED = False  # Set to True once configured
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Your Gmail credentials
EMAIL_ADDRESS = "your-email@gmail.com"  # Your Gmail address
EMAIL_PASSWORD = "your-app-password"  # Gmail App Password (NOT your regular password)

# Email settings
EMAIL_FROM_NAME = "Fanvy"
EMAIL_SUBJECT_VERIFICATION = "Verify Your Email - Fanvy"

# App settings
APP_NAME = "Fanvy"
APP_URL = "http://localhost:5000"  # Change to your actual domain in production
