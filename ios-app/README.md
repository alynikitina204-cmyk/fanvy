# LearnSocial iOS App

A simple iOS wrapper for the LearnSocial Flask web application.

## Setup Instructions

### 1. Open Xcode and Create New Project

1. Open **Xcode** (install from Mac App Store if you don't have it)
2. Click **Create New Project**
3. Select **iOS** → **App**
4. Fill in:
   - Product Name: `LearnSocial`
   - Team: Your Apple ID
   - Organization Identifier: `com.yourname` (or any reverse domain)
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: None
5. Save it anywhere you want (Desktop or Documents)

### 2. Replace Default Files

Replace the following files in your Xcode project with the ones from this `ios-app` folder:
- `LearnSocialApp.swift` → replace the default app file
- `ContentView.swift` → replace ContentView
- `Info.plist` → replace Info.plist

### 3. Start Your Flask Backend

Before running the iOS app, make sure your Flask server is running:

```bash
cd /Users/hk/learnsocial
python3 app.py
```

The server should be running on `http://127.0.0.1:5000`

### 4. Run the iOS App

1. In Xcode, select a simulator (e.g., iPhone 15 Pro)
2. Press **⌘ + R** or click the Play button
3. The app will open and load your Flask web app inside

## Features

- Full WebView wrapper
- Media playback support (audio/video)
- Back/forward gesture navigation
- Allows local networking (connects to localhost:5000)

## Testing on Real Device

To test on your actual iPhone:

1. Connect your iPhone via USB
2. In Xcode, select your iPhone as the target device
3. You may need to trust your Apple ID in iPhone Settings → General → VPN & Device Management
4. Your Flask app needs to be accessible from your network:
   ```bash
   python3 app.py --host=0.0.0.0
   ```
5. Update `ContentView.swift` to use your Mac's IP address instead of `127.0.0.1`:
   ```swift
   WebView(url: URL(string: "http://YOUR_MAC_IP:5000")!)
   ```

## Customization

- **Change app icon**: Add App Icon in Assets.xcassets
- **Change URL**: Edit the URL in `ContentView.swift`
- **Add splash screen**: Modify `UILaunchScreen` in Info.plist

## Note

This is a test/development wrapper. For production:
- Consider proper iOS app architecture
- Add offline support
- Implement native features (notifications, camera, etc.)
- Use proper app signing and provisioning
