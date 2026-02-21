# Alternative: Progressive Web App (No Xcode Required!)

If you don't want to use Xcode, you can make LearnSocial installable on iOS as a PWA.

## What's needed:

1. **Add manifest.json to your Flask app** (already created in this folder)
2. **Add meta tags** to your base.html
3. **Add to Home Screen** from iPhone Safari

## Setup (2 minutes)

### 1. Copy manifest.json to your Flask static folder

```bash
cp ios-app/manifest.json static/manifest.json
```

### 2. Add these lines to your `templates/base.html` (in the `<head>` section):

```html
<!-- PWA Support -->
<link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="LearnSocial">
<meta name="theme-color" content="#4A90E2">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

### 3. Access from iPhone

1. **On your Mac**, find your local IP address:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   Example: `192.168.1.100`

2. **Start Flask with network access:**
   ```bash
   python3 app.py --host=0.0.0.0
   ```

3. **On your iPhone:**
   - Connect to same WiFi as your Mac
   - Open Safari
   - Go to `http://YOUR_MAC_IP:5000`
   - Tap the **Share** button (square with arrow)
   - Tap **Add to Home Screen**
   - Tap **Add**

4. **Done!** The app icon appears on your home screen like a native app!

## Benefits of PWA:

✅ No Xcode required  
✅ No Apple Developer account needed  
✅ Works on iPhone AND Android  
✅ Automatic updates when you change code  
✅ Can work offline with service workers  
✅ Looks like a native app  

## Limitations:

❌ Limited access to device features (camera requires web APIs)  
❌ No App Store distribution  
❌ Notifications require service workers  
❌ Some iOS Safari limitations  

## Best For:

Testing your app quickly on real devices without any setup!
