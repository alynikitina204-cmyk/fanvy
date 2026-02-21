"""
Email Service for Fanvy
Sends verification codes and notifications via Gmail SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Try to import email config, provide defaults if not available
try:
    import email_config
    EMAIL_CONFIGURED = (
        hasattr(email_config, 'EMAIL_ADDRESS') and 
        hasattr(email_config, 'EMAIL_PASSWORD') and
        hasattr(email_config, 'EMAIL_ENABLED') and
        email_config.EMAIL_ADDRESS != "your-email@gmail.com" and
        email_config.EMAIL_PASSWORD != "your-app-password" and
        email_config.EMAIL_ENABLED
    )
except (ImportError, Exception) as e:
    EMAIL_CONFIGURED = False
    print(f"⚠️  Email not configured: {e}")
    # Create a mock email_config to prevent attribute errors
    class MockConfig:
        EMAIL_ENABLED = False
        EMAIL_ADDRESS = "noreply@example.com"
        EMAIL_FROM_NAME = "Fanvy"
        EMAIL_SUBJECT_VERIFICATION = "Verify Your Email - Fanvy"
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
    email_config = MockConfig()

def send_verification_email(to_email, username, verification_code):
    """
    Send verification code email to user
    
    Args:
        to_email: Recipient email address
        username: User's username
        verification_code: 6-digit verification code
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not EMAIL_CONFIGURED:
        print(f"⚠️  Email not configured - verification code for {to_email}: {verification_code}")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{email_config.EMAIL_FROM_NAME} <{email_config.EMAIL_ADDRESS}>"
        msg['To'] = to_email
        msg['Subject'] = email_config.EMAIL_SUBJECT_VERIFICATION
        
        # Email body (HTML version)
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #6366f1; }}
                .code-box {{ background: #f0f0f0; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }}
                .code {{ font-size: 36px; font-weight: bold; color: #6366f1; letter-spacing: 8px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚀 {email_config.APP_NAME}</div>
                </div>
                
                <h2>Hi {username}! 👋</h2>
                <p>Welcome to {email_config.APP_NAME}! To complete your registration, please verify your email address.</p>
                
                <p>Your verification code is:</p>
                
                <div class="code-box">
                    <div class="code">{verification_code}</div>
                </div>
                
                <p>Enter this code on the verification page to activate your account.</p>
                
                <p style="color: #888; font-size: 14px;">
                    This code will expire in 15 minutes. If you didn't create an account, you can safely ignore this email.
                </p>
                
                <div class="footer">
                    <p>© 2026 {email_config.APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version (fallback)
        text_body = f"""
Hi {username}!

Welcome to {email_config.APP_NAME}! To complete your registration, please verify your email address.

Your verification code is: {verification_code}

Enter this code on the verification page to activate your account.

This code will expire in 15 minutes. If you didn't create an account, you can safely ignore this email.

© 2026 {email_config.APP_NAME}
        """
        
        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via Gmail SMTP
        server = smtplib.SMTP(email_config.SMTP_SERVER, email_config.SMTP_PORT)
        server.starttls()  # Enable encryption
        server.login(email_config.EMAIL_ADDRESS, email_config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Verification email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False

def send_approval_notification(to_email, username):
    """
    Send email when admin approves user's account
    
    Args:
        to_email: User's email
        username: User's username
    
    Returns:
        bool: True if sent successfully
    """
    if not EMAIL_CONFIGURED:
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{email_config.EMAIL_FROM_NAME} <{email_config.EMAIL_ADDRESS}>"
        msg['To'] = to_email
        msg['Subject'] = f"Account Approved - {email_config.APP_NAME}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 28px; font-weight: bold; color: #10b981; }}
                .btn {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">✅ {email_config.APP_NAME}</div>
                </div>
                
                <h2>Great News, {username}! 🎉</h2>
                <p>Your account has been approved by our admin team. You can now login and start using {email_config.APP_NAME}!</p>
                
                <a href="{email_config.APP_URL}/login" class="btn">Login Now</a>
                
                <p style="margin-top: 30px; color: #888; font-size: 14px;">
                    Welcome to our community! If you have any questions, feel free to reach out.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Great News, {username}!

Your account has been approved by our admin team. You can now login and start using {email_config.APP_NAME}!

Login at: {email_config.APP_URL}/login

Welcome to our community!
        """
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        server = smtplib.SMTP(email_config.SMTP_SERVER, email_config.SMTP_PORT)
        server.starttls()
        server.login(email_config.EMAIL_ADDRESS, email_config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Approval email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send approval email: {e}")
        return False
